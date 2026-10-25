"""Pipeline di traduzione (M4): cache → prompt → provider → riparazione → cache.

Responsabilità e limiti:

- decide **cosa** chiedere (cache hit, chunking) e **quante volte** ritentare;
- non conosce HTTP (delegato ai provider) né il formato delle risposte (``json_repair``);
- non inventa traduzioni: se una chiave manca finisce in ``TranslationOutcome.missing``
  e il chiamante decide (issue QA, retry mirato, blocco). Il fallback silenzioso
  all'originale — difetto §11.2/3 della Gen 2 — è qui **impossibile**;
- scrive in cache **solo** traduzioni realmente ottenute (difetto §11.2/4 corretto).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass

from pdfbook.domain.models import TranslationSettings
from pdfbook.translation.cache import TranslationCache
from pdfbook.translation.json_repair import JsonRepairError, parse_json_object
from pdfbook.translation.prompts import (
    build_shorten_payload,
    build_shorten_prompt,
    build_translation_prompt,
    build_user_payload,
)
from pdfbook.translation.providers.base import CompletionPort, ProviderError

__all__ = ["DEFAULT_MAX_CHARS", "TranslationOutcome", "TranslationPipeline"]

log = logging.getLogger(__name__)

DEFAULT_MAX_CHARS = 6000
DEFAULT_ATTEMPTS = 3
DEFAULT_BACKOFF = 1.5
_SHORT_PREFIX = "[short]"


@dataclass(frozen=True)
class TranslationOutcome:
    """Risultato di un batch: traduzioni, chiavi mancanti, riuso della cache."""

    translations: Mapping[str, str]
    missing: tuple[str, ...] = ()
    cached: int = 0
    requested: int = 0

    @property
    def complete(self) -> bool:
        return not self.missing

    def __len__(self) -> int:
        return len(self.translations)


class TranslationPipeline:
    """Orchestrazione della traduzione di un batch, con retry e cache partizionata."""

    def __init__(
        self,
        *,
        provider: CompletionPort,
        cache: TranslationCache,
        settings: TranslationSettings,
        max_chars: int = DEFAULT_MAX_CHARS,
        attempts: int = DEFAULT_ATTEMPTS,
        backoff: float = DEFAULT_BACKOFF,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if attempts < 1:
            raise ValueError("attempts deve essere >= 1")
        if max_chars < 1:
            raise ValueError("max_chars deve essere >= 1")
        self.provider = provider
        self.cache = cache
        self.settings = settings
        self.max_chars = max_chars
        self.attempts = attempts
        self.backoff = backoff
        self.sleep = sleep

    # ---------- API ----------

    def translate(
        self,
        batch: Mapping[str, str],
        context: str | None = None,
    ) -> TranslationOutcome:
        """Traduce il batch; le chiavi non ottenute finiscono in ``missing``."""
        cleaned, blanks = self._split_blanks(batch)
        translations: dict[str, str] = dict(blanks)
        hits, pending = self._from_cache(cleaned)
        translations.update(hits)
        for chunk in self._chunks(pending):
            for key, value in self._translate_chunk(chunk, context).items():
                translations[key] = value
        missing = tuple(key for key in pending if key not in translations)
        return TranslationOutcome(
            translations=translations,
            missing=missing,
            cached=len(hits),
            requested=len(pending),
        )

    def shorten(self, original: str, current: str, max_chars: int) -> str:
        """Versione più corta della traduzione, o ``current`` se non è possibile."""
        if max_chars <= 0 or not original.strip():
            return current
        cache_text = f"{_SHORT_PREFIX}{max_chars}|{original}"
        cached = self.cache.get(cache_text)
        if cached:
            return cached
        system = build_shorten_prompt(
            self.settings.target_lang, max_chars, glossary=self.settings.glossary
        )
        payload = build_shorten_payload(original, current, max_chars)
        try:
            parsed = self._call_with_retries(system, payload, ("short",))
        except ProviderError as exc:
            log.warning("ritraduzione non riuscita (%s): %s", self.provider.name, exc)
            return current
        short = parsed.get("short", "").strip()
        if not short or len(short) >= len(current):
            return current
        self.cache.put(cache_text, short)
        return short

    # ---------- passi ----------

    def _split_blanks(self, batch: Mapping[str, str]) -> tuple[dict[str, str], dict[str, str]]:
        cleaned: dict[str, str] = {}
        blanks: dict[str, str] = {}
        for key, value in batch.items():
            text = str(value)
            if text.strip():
                cleaned[key] = text.strip()
            else:
                blanks[key] = ""
        return cleaned, blanks

    def _from_cache(self, cleaned: Mapping[str, str]) -> tuple[dict[str, str], dict[str, str]]:
        hits: dict[str, str] = {}
        pending: dict[str, str] = {}
        for key, text in cleaned.items():
            cached = self.cache.get(text)
            if cached is None:
                pending[key] = text
            else:
                hits[key] = cached
        return hits, pending

    def _chunks(self, pending: Mapping[str, str]) -> Iterator[dict[str, str]]:
        chunk: dict[str, str] = {}
        size = 0
        for key, text in pending.items():
            cost = len(text) + len(key) + 6
            if chunk and size + cost > self.max_chars:
                yield chunk
                chunk, size = {}, 0
            chunk[key] = text
            size += cost
        if chunk:
            yield chunk

    def _translate_chunk(self, chunk: Mapping[str, str], context: str | None) -> dict[str, str]:
        system = build_translation_prompt(
            self.settings.target_lang,
            glossary=self.settings.glossary,
            context=context,
        )
        parsed = self._call_with_retries(system, build_user_payload(chunk), tuple(chunk))
        accepted = {key: value for key, value in parsed.items() if chunk.get(key) and value}
        self._store(chunk, accepted)
        return accepted

    def _store(self, chunk: Mapping[str, str], accepted: Mapping[str, str]) -> None:
        if accepted:
            self.cache.put_many({chunk[key]: value for key, value in accepted.items()})

    def _call_with_retries(self, system: str, user: str, keys: Iterable[str]) -> dict[str, str]:
        expected = tuple(keys)
        last_error: Exception | None = None
        for attempt in range(1, self.attempts + 1):
            try:
                raw = self.provider.complete(system, user)
                parsed = parse_json_object(raw, expected_keys=expected)
                if not parsed:
                    raise JsonRepairError("risposta senza chiavi utili", raw)
                return parsed
            except (ProviderError, JsonRepairError) as exc:
                last_error = exc
                log.warning(
                    "tentativo %s/%s fallito (%s): %s",
                    attempt, self.attempts, self.provider.name, exc,
                )
                if attempt < self.attempts:
                    self.sleep(self.backoff ** attempt)
        raise ProviderError(
            f"{self.provider.name}: traduzione fallita dopo {self.attempts} tentativi "
            f"({type(last_error).__name__}: {last_error})"
        )
