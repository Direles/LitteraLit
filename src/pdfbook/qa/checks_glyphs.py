"""Controllo dei glifi e della copertura testuale (P0.5).

Confronta ciò che **doveva** comparire sulla pagina tradotta con ciò che è effettivamente
estratto dal PDF prodotto. Rileva due classi di difetti misurati nel progetto:

1. **caratteri tipografici persi o sostituiti** (em-dash → `·`, virgolette → `"`),
   confrontando i conteggi **prima** della normalizzazione;
2. **testo mancante**, confrontando i token dopo la normalizzazione (NBSP e soft hyphen
   non devono generare falsi allarmi).

Non rileva errori di traduzione: quello non è verificabile senza un riferimento umano.
"""

from __future__ import annotations

from collections.abc import Sequence

from pdfbook.domain.models import IssueKind, QAIssue

from .textnorm import count_special, normalize, tokens

__all__ = ["LOST_TOKEN_RATIO", "check_page_glyphs"]

# Frazione di token persi oltre la quale si considera il testo mancante (non solo un glifo).
LOST_TOKEN_RATIO = 0.30
_MIN_TOKENS = 5
_SAMPLE_CHARS = 40


def check_page_glyphs(
    page_number: int,
    expected_segments: Sequence[str],
    actual_text: str,
) -> list[QAIssue]:
    """Issue della pagina: glifi tipografici persi e testo mancante."""
    expected = " ".join(segment for segment in expected_segments if segment and segment.strip())
    if not expected.strip():
        return []
    issues: list[QAIssue] = []
    issues.extend(_special_character_issues(page_number, expected, actual_text))
    issues.extend(_missing_text_issues(page_number, expected, actual_text))
    return issues


def _special_character_issues(page_number: int, expected: str, actual: str) -> list[QAIssue]:
    expected_counts = count_special(expected)
    actual_counts = count_special(actual)
    issues: list[QAIssue] = []
    for char, expected_count in sorted(expected_counts.items()):
        missing = expected_count - actual_counts.get(char, 0)
        if missing > 0:
            issues.append(
                QAIssue(
                    page=page_number,
                    kind=IssueKind.GLYPH_MISSING,
                    detail=f"'{char}' (U+{ord(char):04X}): {expected_count} attesi, "
                    f"{expected_count - missing} resi",
                )
            )
    return issues


def _missing_text_issues(page_number: int, expected: str, actual: str) -> list[QAIssue]:
    expected_tokens = tokens(expected)
    if len(expected_tokens) < _MIN_TOKENS:
        return []
    actual_tokens = tokens(actual)
    missing = len(expected_tokens) - _matched_tokens(expected_tokens, actual_tokens)
    ratio = missing / len(expected_tokens)
    if ratio <= LOST_TOKEN_RATIO:
        return []
    sample = _first_missing_sample(expected, actual)
    return [
        QAIssue(
            page=page_number,
            kind=IssueKind.TEXT_MISSING,
            detail=f"{missing}/{len(expected_tokens)} parole non trovate nel PDF "
            f"({ratio:.0%}), es. {sample!r}",
        )
    ]


def _matched_tokens(expected: Sequence[str], actual: Sequence[str]) -> int:
    """Token attesi presenti nel reso, contati una volta ciascuno (multiset)."""
    remaining: dict[str, int] = {}
    for token in actual:
        remaining[token] = remaining.get(token, 0) + 1
    matched = 0
    for token in expected:
        available = remaining.get(token, 0)
        if available:
            remaining[token] = available - 1
            matched += 1
    return matched


def _first_missing_sample(expected: str, actual: str) -> str:
    actual_tokens = set(tokens(actual))
    for token in tokens(expected):
        if token not in actual_tokens:
            return token[:_SAMPLE_CHARS]
    return normalize(expected)[:_SAMPLE_CHARS]
