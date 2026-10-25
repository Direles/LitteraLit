"""Translation memory con chiave composta (migrazione M3).

Corregge il difetto storico della Gen 2: la cache usava ``md5(testo)`` come unica chiave,
perciò una traduzione ottenuta con un certo provider/modello/lingua veniva riusata per
qualunque altro contesto (cache poisoning silenzioso, §11.2/2).

Qui la chiave include **obbligatoriamente** la partizione di configurazione
(``TranslationSettings.cache_partition()``: provider + modello + lingua + glossario),
più il testo normalizzato e una versione dello schema.

Altre proprietà:

- scrittura **atomica** (file temporaneo nella stessa directory + ``os.replace``);
- accesso **thread-safe** (lock rientrante, in vista del parallelismo per pagina);
- un file corrotto non blocca l'esecuzione: viene registrato un warning e si riparte vuoti;
- nessun ``print``: solo ``logging`` (R13).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from collections.abc import Mapping
from pathlib import Path

from pdfbook.domain.models import TranslationSettings

from .cache_prune import prune

__all__ = ["CACHE_VERSION", "TranslationCache", "make_key"]

CACHE_VERSION = 2
_SEP = "\x1f"
_DEFAULT_AUTOSAVE = 25

log = logging.getLogger(__name__)


def make_key(text: str, partition: str) -> str:
    """Chiave esadecimale stabile di una voce: partizione + testo normalizzato."""
    if not partition:
        raise ValueError("partizione obbligatoria: la cache non può essere globale")
    payload = f"{CACHE_VERSION}{_SEP}{partition}{_SEP}{text.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TranslationCache:
    """Dizionario persistente ``chiave -> traduzione`` con salvataggio atomico."""

    def __init__(
        self,
        path: str | os.PathLike[str],
        partition: str,
        *,
        autosave_every: int = _DEFAULT_AUTOSAVE,
    ) -> None:
        if not partition:
            raise ValueError("partizione obbligatoria")
        self.path = Path(path)
        self.partition = partition
        self.autosave_every = max(0, autosave_every)
        self.hits = 0
        self.misses = 0
        self._entries: dict[str, object] | None = None
        self._pending = 0
        self._dirty = False
        self._lock = threading.RLock()

    @classmethod
    def for_settings(
        cls,
        path: str | os.PathLike[str],
        settings: TranslationSettings,
        **kwargs: object,
    ) -> TranslationCache:
        return cls(path, settings.cache_partition(), **kwargs)  # type: ignore[arg-type]

    # ---------- lettura/scrittura ----------

    def get(self, text: str) -> str | None:
        with self._lock:
            raw = self._data().get(make_key(text, self.partition))
            value = _value(raw)
            if value is None:
                self.misses += 1
            else:
                self.hits += 1
            return value

    def contains(self, text: str) -> bool:
        with self._lock:
            return make_key(text, self.partition) in self._data()

    def put(self, text: str, translation: str) -> None:
        with self._lock:
            key = make_key(text, self.partition)
            if _value(self._data().get(key)) == translation:
                return
            self._data()[key] = {"v": translation, "t": int(time.time())}
            self._dirty = True
            self._pending += 1
            if self.autosave_every and self._pending >= self.autosave_every:
                self.save()

    def put_many(self, pairs: Mapping[str, str]) -> int:
        """Inserisce ``{testo_originale: traduzione}``; restituisce quante voci sono nuove."""
        added = 0
        with self._lock:
            for text, translation in pairs.items():
                if not text.strip():
                    continue
                if self.get(text) != translation:
                    self.put(text, translation)
                    added += 1
        return added

    def save(self) -> bool:
        """Scrive su disco in modo atomico. ``False`` se la scrittura è fallita."""
        with self._lock:
            if self._entries is None:
                return True
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.path.with_name(self.path.name + ".tmp")
                with tmp.open("w", encoding="utf-8") as handle:
                    json.dump(self._entries, handle, ensure_ascii=False)
                os.replace(tmp, self.path)
            except OSError as exc:
                log.warning("cache non salvata in %s: %s", self.path, exc)
                return False
            self._pending = 0
            self._dirty = False
            return True

    # ---------- introspezione ----------

    @property
    def entries(self) -> int:
        with self._lock:
            return len(self._data())

    @property
    def dirty(self) -> bool:
        with self._lock:
            return self._dirty

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "entries": len(self._data()),
                "hits": self.hits,
                "misses": self.misses,
                "bytes": self.size_bytes(),
            }

    def size_bytes(self) -> int:
        try:
            return self.path.stat().st_size
        except OSError:
            return 0

    # ---------- manutenzione ----------

    @classmethod
    def for_maintenance(cls, path: str | os.PathLike[str]) -> TranslationCache:
        """Cache aperta senza partizione: serve solo a ``prune``/``stats``, non a tradurre."""
        return cls(path, "maintenance", autosave_every=0)

    def prune(
        self,
        *,
        max_entries: int | None = None,
        max_age_days: float | None = None,
    ) -> int:
        """Elimina le voci vecchie o in eccesso; restituisce quante ne ha rimosse."""
        with self._lock:
            kept, removed = prune(
                self._data(), max_entries=max_entries, max_age_days=max_age_days
            )
            if removed or kept != self._data():
                self._entries = dict(kept)
                self._dirty = True
                self.save()
            return removed

    # ---------- interno ----------

    def _data(self) -> dict[str, object]:
        if self._entries is None:
            self._entries = self._load()
        return self._entries

    def _load(self) -> dict[str, object]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("cache illeggibile (%s): riparto da vuota", exc)
            return {}
        if not isinstance(raw, dict):
            log.warning("cache con formato inatteso in %s: riparto da vuota", self.path)
            return {}
        return {str(k): v for k, v in raw.items() if _value(v) is not None}


def _value(raw: object) -> str | None:
    """Estrae la traduzione sia dal formato corrente sia da quello legacy."""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        value = raw.get("v")
        return value if isinstance(value, str) else None
    return None
