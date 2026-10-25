"""Memoria terminologica per libro (Fase 5.3).

Un glossario scritto a mano è meglio, ma nessuno lo scrive prima di tradurre. Questa memoria
osserva il libro e propone i termini che **ricorrono e sembrano nomi propri o gergo**:
maiuscole interne, acronimi, sequenze di parole capitalizzate ("Agile Estimating"), parole
lunghe ripetute in pagine diverse.

Le proposte non entrano mai da sole nella traduzione: sono un file da rivedere. Il criterio
è conservativo (frequenza + forma), perché un falso positivo costa una traduzione sbagliata
in tutto il libro.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

__all__ = [
    "MAX_TERMS",
    "MIN_LENGTH",
    "MIN_OCCURRENCES",
    "Term",
    "Terminology",
    "candidates",
    "glossary_lines",
]

MIN_LENGTH = 4
MIN_OCCURRENCES = 3
MAX_TERMS = 80

_WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ0-9'’\-]*")
_SENTENCE_START = re.compile(r"(?:^|[.!?:;»\"]\s+)$")
_STOP_START = frozenset(
    {
        "The", "This", "That", "These", "Those", "There", "Their", "Then", "They", "When",
        "What", "Which", "While", "With", "Where", "Why", "How", "If", "In", "It",
        "Its", "But", "And", "Or", "For", "From", "On", "At", "As", "By", "To", "We", "You",
        "He", "She", "His", "Her", "Our", "Your", "Chapter", "Part", "Figure", "Table",
    }
)


@dataclass(frozen=True)
class Term:
    """Un candidato: testo normalizzato, quante volte compare, in quante pagine."""

    text: str
    occurrences: int
    pages: int


@dataclass
class Terminology:
    """Accumula i termini di un libro pagina per pagina."""

    min_occurrences: int = MIN_OCCURRENCES
    counts: Counter[str] = field(default_factory=Counter)
    pages: dict[str, set[int]] = field(default_factory=dict)

    def observe(self, page: int, texts: Iterable[str]) -> None:
        """Registra i termini candidati presenti nei testi di una pagina."""
        for text in texts:
            for term in _terms_in(text):
                self.counts[term] += 1
                self.pages.setdefault(term, set()).add(page)

    def candidates(self, *, limit: int = MAX_TERMS) -> list[Term]:
        """Termini ricorrenti, dal più frequente; a parità, ordine alfabetico."""
        terms = [
            Term(text, count, len(self.pages.get(text, ())))
            for text, count in self.counts.items()
            if count >= self.min_occurrences
            and (len(text) >= MIN_LENGTH or _is_acronym(text))
        ]
        terms.sort(key=lambda term: (-term.occurrences, -term.pages, term.text))
        return terms[: max(0, limit)]

    def glossary_lines(self, *, limit: int = MAX_TERMS) -> list[str]:
        return [term.text for term in self.candidates(limit=limit)]


def candidates(texts: Iterable[str], *, min_occurrences: int = MIN_OCCURRENCES) -> list[Term]:
    """Scorciatoia su un corpus già in memoria."""
    memory = Terminology(min_occurrences=min_occurrences)
    for index, text in enumerate(texts, start=1):
        memory.observe(index, [text])
    return memory.candidates()


def glossary_lines(terms: Mapping[str, int] | Iterable[Term]) -> list[str]:
    """Righe pronte per un file di glossario (un termine per riga)."""
    if isinstance(terms, Mapping):
        return [text for text, count in terms.items() if count >= MIN_OCCURRENCES]
    return [term.text for term in terms]


def _terms_in(text: str) -> set[str]:
    """Nomi propri, acronimi e sequenze capitalizzate; esclude gli inizi di frase."""
    found: set[str] = set()
    buffer: list[str] = []
    buffer_at_start = False
    for match in _WORD.finditer(text):
        word = match.group(0)
        sentence_start = match.start() == 0 or bool(_SENTENCE_START.search(text[: match.start()]))
        if _is_acronym(word):
            _flush(found, buffer, buffer_at_start)
            buffer, buffer_at_start = [], False
            found.add(word)
            continue
        if word[0].isupper() and not (sentence_start and word in _STOP_START):
            if not buffer:
                buffer_at_start = sentence_start
            buffer.append(word)
            continue
        _flush(found, buffer, buffer_at_start)
        buffer, buffer_at_start = [], False
        if _is_technical(word):
            found.add(word)
    _flush(found, buffer, buffer_at_start)
    return {
        term.strip()
        for term in found
        if len(term.strip()) >= MIN_LENGTH or _is_acronym(term.strip())
    }


def _flush(found: set[str], buffer: list[str], at_start: bool) -> None:
    """Aggiunge il gruppo capitalizzato, scartando la parola iniziale di frase.

    L'eccezione è il gergo riconoscibile (`JavaScript`, `iOS`): anche a inizio frase è un
    termine, non una parola qualsiasi.
    """
    if not buffer:
        return
    if len(buffer) == 1 and at_start:
        if _is_technical(buffer[0]):
            found.add(buffer[0])
        return
    found.add(" ".join(buffer))


def _is_acronym(word: str) -> bool:
    letters = [char for char in word if char.isalpha()]
    return len(letters) >= 2 and all(char.isupper() for char in letters)


def _is_technical(word: str) -> bool:
    """Parola lunga con maiuscola interna o trattino: probabile gergo del libro."""
    return len(word) >= 8 and (any(char.isupper() for char in word[1:]) or "-" in word)
