"""Sillabazione nella lingua di destinazione (M6).

``pyphen`` è **opzionale**: se manca, il sistema non finge di sillabare — ``available``
resta ``False`` e il fitting va a capo solo sugli spazi (R14: capacità degradata
dichiarata, non nascosta).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

__all__ = ["LANG_CODES", "MIN_WORD_LENGTH", "Hyphenation"]

try:  # pragma: no cover - dipende dall'ambiente
    import pyphen
except ImportError:  # pragma: no cover
    pyphen = None  # type: ignore[assignment]

LANG_CODES = {
    "Italiano": "it_IT",
    "Inglese": "en_US",
    "Spagnolo": "es",
    "Francese": "fr",
    "Tedesco": "de_DE",
}

MIN_WORD_LENGTH = 6
_DEFAULT_BACKEND = object()


class Hyphenation:
    """Spezza le parole in sillabe compatibili con lo spazio disponibile."""

    def __init__(
        self,
        target_lang: str = "Italiano",
        *,
        module: Any = _DEFAULT_BACKEND,
        min_word_length: int = MIN_WORD_LENGTH,
    ) -> None:
        self.min_word_length = min_word_length
        self.language = target_lang
        self.available = False
        self._dictionary = None
        backend = pyphen if module is _DEFAULT_BACKEND else module
        code = LANG_CODES.get(target_lang)
        if backend is not None and code:
            try:
                self._dictionary = backend.Pyphen(lang=code)
                self.available = True
            except Exception:  # noqa: BLE001 - dizionario mancante per quella lingua
                self._dictionary = None

    def pairs(self, word: str) -> Iterable[tuple[str, str]]:
        """Coppie ``(prefisso, suffisso)`` dalla più lunga alla più corta."""
        if self._dictionary is None or len(word) < self.min_word_length:
            return ()
        try:
            return tuple(self._dictionary.iterate(word))
        except Exception:  # noqa: BLE001 - parola anomala: nessuna sillabazione
            return ()

    def split_for_width(
        self,
        word: str,
        width_of: Callable[[str], float],
        available: float,
    ) -> tuple[str, str] | None:
        """Prima sillabazione che entra in ``available``, con il trattino incluso."""
        if available <= 0:
            return None
        for prefix, suffix in self.pairs(word):
            candidate = prefix + "-"
            if width_of(candidate) <= available:
                return candidate, suffix
        return None
