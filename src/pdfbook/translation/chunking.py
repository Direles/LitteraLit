"""Chunking per frase (Fase 5.2).

Il chunking per blocchi ha un difetto: se **un singolo blocco** supera il budget di caratteri
finisce in una richiesta enorme, e i modelli iniziano a troncare o a saltare chiavi. Qui si
spezza prima sui confini di frase, e solo se una frase è ancora troppo lunga si scende al
confine di parola.

Le chiavi dei pezzi sono ``chiave#0``, ``chiave#1``…: la pipeline le riunisce dopo la
traduzione, quindi il resto del sistema continua a vedere una chiave sola.

Niente spaCy (una dipendenza da centinaia di MB per un compito che qui è regex + punti): il
prezzo è qualche falso confine con le abbreviazioni, gestito da una lista breve.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

__all__ = ["PART_SEPARATOR", "join_parts", "split_long_unit", "split_parts", "split_sentences"]

#: Separatore fra chiave base e indice del pezzo.
PART_SEPARATOR = "#"

_SENTENCE_END = re.compile(r"[.!?…]+[\"'”’»)\]]*\s+")
_ABBREVIATIONS = (
    "e.g.",
    "i.e.",
    "etc.",
    "vs.",
    "cfr.",
    "pag.",
    "fig.",
    "tab.",
    "cap.",
    "n.",
    "no.",
    "mr.",
    "mrs.",
    "ms.",
    "dr.",
    "prof.",
    "st.",
    "s.",
)


def split_sentences(text: str) -> list[str]:
    """Divide il testo in frasi, senza perdere caratteri (gli spazi restano in coda)."""
    stripped = text.strip()
    if not stripped:
        return []
    parts: list[str] = []
    start = 0
    for match in _SENTENCE_END.finditer(stripped):
        candidate = stripped[start : match.start() + 1]
        if _ends_with_abbreviation(candidate):
            continue
        parts.append(stripped[start : match.end()])
        start = match.end()
    if start < len(stripped):
        parts.append(stripped[start:])
    return [part for part in (item.strip() for item in parts) if part]


def split_long_unit(key: str, text: str, max_chars: int) -> list[tuple[str, str]]:
    """Spezza un'unità troppo lunga in pezzi ``chiave#i`` che rispettano ``max_chars``."""
    limit = max(1, max_chars)
    if len(text) <= limit:
        return [(key, text)]
    chunks: list[str] = []
    current = ""
    for sentence in split_sentences(text):
        for piece in _split_sentence(sentence, limit):
            if current and len(current) + len(piece) + 1 > limit:
                chunks.append(current)
                current = piece
            elif current:
                current = f"{current} {piece}"
            else:
                current = piece
    if current:
        chunks.append(current)
    if len(chunks) <= 1:
        return [(key, text)]
    return [(f"{key}{PART_SEPARATOR}{index}", chunk) for index, chunk in enumerate(chunks)]


def split_parts(keys: Mapping[str, str]) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Separa chiavi intere e pezzi: ``{"a#0": x}`` → ``({}, {"a": ["a#0"]})``."""
    whole: dict[str, str] = {}
    parts: dict[str, list[str]] = {}
    for key in keys:
        base, separator, index = key.partition(PART_SEPARATOR)
        if separator and index.isdigit():
            parts.setdefault(base, []).append(key)
        else:
            whole[key] = key
    for items in parts.values():
        items.sort(key=lambda item: int(item.rsplit(PART_SEPARATOR, 1)[1]))
    return whole, parts


def join_parts(base: str, parts: Mapping[str, str], *, expected: int | None = None) -> str | None:
    """Ricompone i pezzi tradotti; ``None`` se ne manca uno (o se ``expected`` non torna)."""
    keys = _ordered_keys(base, parts)
    if not keys:
        return None
    if expected is not None and len(keys) != expected:
        return None
    values = [parts[key] for key in keys]
    if any(not value for value in values):
        return None
    return " ".join(values).strip()


def _ordered_keys(base: str, parts: Mapping[str, str]) -> list[str]:
    keys = [
        key
        for key in parts
        if key.partition(PART_SEPARATOR)[0] == base and key.partition(PART_SEPARATOR)[2].isdigit()
    ]
    return sorted(keys, key=lambda item: int(item.rsplit(PART_SEPARATOR, 1)[1]))


def _split_sentence(sentence: str, limit: int) -> list[str]:
    """Spezza una frase più lunga del limite sui confini di parola."""
    if len(sentence) <= limit:
        return [sentence]
    pieces: list[str] = []
    current = ""
    for word in sentence.split():
        if current and len(current) + len(word) + 1 > limit:
            pieces.append(current)
            current = word
        elif current:
            current = f"{current} {word}"
        else:
            current = word
    if current:
        pieces.append(current)
    return pieces


def _ends_with_abbreviation(text: str) -> bool:
    tail = text.strip().lower()
    return any(tail.endswith(abbreviation) for abbreviation in _ABBREVIATIONS)
