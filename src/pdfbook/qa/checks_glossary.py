"""Verifica del glossario (Fase 5.1).

Il glossario è un vincolo: un termine elencato deve restare **così com'è** nel testo
tradotto. Qui si controlla l'effetto, non si corregge: ogni violazione diventa una issue
con il termine mancante.

Confronto senza dipendenze: normalizzazione di spazi e maiuscole, ricerca di sottostringa.
Nessun fuzzy matching: un falso positivo qui costa più di un falso negativo.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from pdfbook.domain.models import IssueKind, QAIssue

__all__ = ["check_glossary", "contains_term", "normalize"]

_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    return _SPACES.sub(" ", text or "").strip().lower()


def contains_term(text: str, term: str) -> bool:
    """``True`` se il termine compare nel testo ignorando spazi e maiuscole."""
    cleaned = normalize(term)
    return bool(cleaned) and cleaned in normalize(text)


def check_glossary(
    page_number: int,
    originals: Mapping[str, str],
    translations: Mapping[str, str],
    glossary: Sequence[str],
) -> list[QAIssue]:
    """Issue per ogni termine del glossario presente nell'originale e perso nella traduzione."""
    terms = [term.strip() for term in glossary if term and term.strip()]
    if not terms:
        return []
    issues: list[QAIssue] = []
    for key, original in originals.items():
        translated = translations.get(key)
        if not translated:
            continue
        for term in terms:
            if contains_term(original, term) and not contains_term(translated, term):
                issues.append(
                    QAIssue(
                        page=page_number,
                        kind=IssueKind.GLOSSARY_VIOLATION,
                        block=key,
                        detail=f"termine '{term}' non conservato",
                    )
                )
    return issues
