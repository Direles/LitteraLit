"""Normalizzazione del testo estratto da un PDF (P0.5).

PyMuPDF, quando disegna con un TTF, espone gli spazi come **NBSP** (U+00A0) e alcuni
trattini come **soft hyphen** (U+00AD): senza normalizzazione ogni confronto testuale
fallisce e il QA produce falsi allarmi (o, peggio, non vede i veri difetti).

Qui si applica una normalizzazione **conservativa**: si uniformano solo i caratteri che
non hanno valore semantico, mentre la punteggiatura tipografica viene mappata su ASCII
in modo da poter confrontare `—` con `-` senza perdere il conteggio.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable

__all__ = [
    "SPECIAL_CHARS",
    "collapse",
    "count_special",
    "normalize",
    "tokens",
]

# Caratteri tipografici il cui conteggio è un segnale di regressione (difetto §11.2/13).
SPECIAL_CHARS = ("\u2014", "\u2013", "\u2019", "\u201c", "\u201d", "\u00ab", "\u00bb", "\u2026")

_REPLACEMENTS = {
    "\u00a0": " ",  # NBSP → spazio
    "\u00ad": "",  # soft hyphen → rimosso
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2026": "...",
    "\u00ab": '"',
    "\u00bb": '"',
}

_WHITESPACE = re.compile(r"\s+")
_TOKEN = re.compile(r"[\w']+", re.UNICODE)


def normalize(text: str) -> str:
    """Testo confrontabile: NFKC, sostituzioni tipografiche, spazi collassati."""
    decomposed = unicodedata.normalize("NFKC", text or "")
    for source, target in _REPLACEMENTS.items():
        decomposed = decomposed.replace(source, target)
    return collapse(decomposed)


def collapse(text: str) -> str:
    """Spazi multipli e a capo → singolo spazio."""
    return _WHITESPACE.sub(" ", text).strip()


def tokens(text: str) -> list[str]:
    """Parole normalizzate e minuscole (per il confronto multiset)."""
    return [match.lower() for match in _TOKEN.findall(normalize(text))]


def count_special(text: str) -> Counter:
    """Conteggio dei caratteri tipografici **prima** della normalizzazione."""
    return Counter(char for char in (text or "") if char in SPECIAL_CHARS)


def lost_tokens(expected: Iterable[str], actual: Iterable[str]) -> Counter:
    """Token presenti nell'atteso e mancanti nel reso (multiset)."""
    return Counter(tokens(" ".join(expected))) - Counter(tokens(" ".join(actual)))
