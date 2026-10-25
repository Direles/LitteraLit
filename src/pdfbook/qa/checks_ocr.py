"""OCR come giudice, non come estrattore (Fase 4.4).

Il rischio delle scansioni non è l'OCR in sé: è un OCR **sbagliato** che nessuno nota. Qui si
confronta il testo che la pipeline ha usato (strato di testo o VLM) con una seconda lettura
indipendente e si misura la divergenza. Le righe che l'altro motore non vede sono il segnale
più utile: spesso sono didascalie, note o testo in corpo piccolo.

Nessun motore OCR qui dentro: due trascrizioni entrano, un diff esce. Così il controllo si
testa con stringhe e si può collegare a ocrmypdf, a un VLM o a un servizio esterno.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from pdfbook.domain.models import IssueKind, QAIssue

__all__ = [
    "MIN_SIMILARITY",
    "TranscriptDiff",
    "check_transcripts",
    "compare_transcripts",
    "tokens",
]

#: Sotto questa similarità (0–1) la pagina va segnalata.
MIN_SIMILARITY = 0.90
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


@dataclass(frozen=True)
class TranscriptDiff:
    """Esito del confronto fra due letture della stessa pagina."""

    similarity: float
    missing: tuple[str, ...]
    extra: tuple[str, ...]
    words: int

    @property
    def ok(self) -> bool:
        return self.similarity >= MIN_SIMILARITY


def tokens(text: str) -> list[str]:
    """Parole normalizzate (minuscole): la punteggiatura non conta nella similarità."""
    return [word.lower() for word in _WORD.findall(text or "")]


def compare_transcripts(primary: str, secondary: str) -> TranscriptDiff:
    """Confronta la trascrizione usata con quella di controllo."""
    first = tokens(primary)
    second = tokens(secondary)
    if not first and not second:
        return TranscriptDiff(1.0, (), (), 0)
    if not first or not second:
        return TranscriptDiff(0.0, tuple(sorted(set(first) - set(second))), (), len(first))
    counts_first = Counter(first)
    counts_second = Counter(second)
    overlap = sum((counts_first & counts_second).values())
    similarity = 2 * overlap / (len(first) + len(second))
    missing = tuple(sorted((counts_first - counts_second).elements()))
    extra = tuple(sorted((counts_second - counts_first).elements()))
    return TranscriptDiff(
        similarity=round(similarity, 4),
        missing=missing[:20],
        extra=extra[:20],
        words=len(first),
    )


def check_transcripts(
    page: int,
    primary: str,
    secondary: str,
    *,
    min_similarity: float = MIN_SIMILARITY,
) -> list[QAIssue]:
    """Issue informativa quando due letture della stessa pagina divergono troppo."""
    diff = compare_transcripts(primary, secondary)
    if diff.words == 0 or diff.similarity >= min_similarity:
        return []
    sample = ", ".join(diff.missing[:6]) if diff.missing else "nessuna parola in comune"
    return [
        QAIssue(
            page=page,
            kind=IssueKind.SCAN_FALLBACK,
            detail=(
                f"due letture OCR divergono (similarità {diff.similarity:.2f} su "
                f"{diff.words} parole): {sample}"
            ),
        )
    ]
