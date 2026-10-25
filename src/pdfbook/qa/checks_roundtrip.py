"""Round-trip del testo disegnato (Fase 1.5).

Il requisito non negoziabile: ciò che il programma disegna deve restare **testo**, non
disegno. Estrarre di nuovo la pagina appena scritta e confrontarla con ciò che si è chiesto
di disegnare smaschera i casi in cui:

* un font sostitutivo ha perso caratteri (``glyph_missing`` è già bloccante, questo è il
  controllo a valle);
* il testo disegnato è meno del previsto (righe saltate);
* compaiono **NBSP** (U+00A0) o **soft hyphen** (U+00AD): difetto §11.7/1, che degrada
  copia/incolla e ricerca. Qui si contano e si segnalano, invece di lasciarli passare.

La riscrittura del CMap ToUnicode (con ``fontTools``) resta un intervento opzionale: finché
il difetto è raro e misurato, la mitigazione in QA è la scelta proporzionata.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from pdfbook.domain.models import IssueKind, QAIssue
from pdfbook.qa.textnorm import normalize

__all__ = [
    "MIN_ROUNDTRIP",
    "NBSP",
    "SOFT_HYPHEN",
    "check_roundtrip",
    "roundtrip_ratio",
    "special_chars",
]

#: Sotto questa frazione di caratteri ritrovati il round-trip è sospetto.
MIN_ROUNDTRIP = 0.999
#: Percentuale di NBSP/soft hyphen oltre la quale vale la pena segnalare.
SPECIAL_CHAR_LIMIT = 0.002
#: Sotto questo numero assoluto i caratteri speciali sono rumore, non un difetto.
SPECIAL_CHAR_FLOOR = 3

NBSP = "\u00a0"
SOFT_HYPHEN = "\u00ad"


def roundtrip_ratio(expected: Iterable[str], extracted: str) -> float:
    """Frazione di caratteri (non spazio) attesi che si ritrovano nel testo estratto."""
    wanted = _chars(" ".join(expected))
    found = _chars(extracted)
    if not wanted:
        return 1.0
    if not found:
        return 0.0
    return min(len(found), len(wanted)) / len(wanted)


def special_chars(text: str) -> Counter[str]:
    """Conteggio di NBSP e soft hyphen nel testo estratto."""
    counts: Counter[str] = Counter()
    for char in text or "":
        if char == NBSP:
            counts["nbsp"] += 1
        elif char == SOFT_HYPHEN:
            counts["soft_hyphen"] += 1
    return counts


def check_roundtrip(
    page: int,
    expected: Iterable[str],
    extracted: str,
    *,
    min_ratio: float = MIN_ROUNDTRIP,
) -> list[QAIssue]:
    """Issue informative quando il testo estratto non torna con quello disegnato."""
    texts = [text for text in expected if text and text.strip()]
    issues: list[QAIssue] = []
    ratio = roundtrip_ratio(texts, extracted)
    if texts and ratio < min_ratio:
        issues.append(
            QAIssue(
                page=page,
                kind=IssueKind.ROUNDTRIP_LOSS,
                detail=f"round-trip {ratio:.3f} (atteso ≥ {min_ratio:.3f})",
            )
        )
    counts = special_chars(extracted)
    total = counts["nbsp"] + counts["soft_hyphen"]
    length = max(len(extracted), 1)
    if total > SPECIAL_CHAR_FLOOR and total / length > SPECIAL_CHAR_LIMIT:
        issues.append(
            QAIssue(
                page=page,
                kind=IssueKind.SPECIAL_CHAR_LEAK,
                detail=(
                    f"{counts['nbsp']} NBSP e {counts['soft_hyphen']} soft hyphen su "
                    f"{length} caratteri: copia/incolla degradato"
                ),
            )
        )
    return issues


def _chars(text: str) -> str:
    return "".join(char for char in normalize(text) if not char.isspace())
