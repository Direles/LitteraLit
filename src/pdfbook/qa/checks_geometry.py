"""Controllo geometrico dei run disegnati (P0.5).

Verifica due difetti misurati sui libri reali (§14.3a dell'architettura):

- **sovrapposizione** fra righe appartenenti a blocchi diversi (testo che si accavalla);
- **sbandamento** oltre i margini della pagina (testo tagliato o finito fuori foglio).

Lavora su un protocollo strutturale (``PositionedText``): non importa ``rendering`` (R5),
quindi i ``TextRun`` del renderer vanno bene così come sono.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from itertools import combinations
from typing import Protocol, runtime_checkable

from pdfbook.domain.models import IssueKind, QAIssue, Rect

__all__ = [
    "MAX_ISSUES_PER_PAGE",
    "PositionedText",
    "check_page_geometry",
    "run_box",
]

# Soglie: un contatto di 2 pt fra due righe adiacenti è normale, una vera sovrapposizione no.
MIN_VERTICAL_OVERLAP = 2.0
MIN_OVERLAP_RATIO = 0.25
MIN_OVERLAP_AREA = 4.0
PAGE_TOLERANCE = 2.0
ASCENT_RATIO = 0.80
DESCENT_RATIO = 0.25
MAX_ISSUES_PER_PAGE = 20


@runtime_checkable
class PositionedText(Protocol):
    """Tutto ciò che serve al controllo geometrico di una riga disegnata."""

    x: float
    baseline_y: float
    text: str
    size: float
    width: float
    block_id: str


def run_box(item: PositionedText) -> Rect:
    """Rettangolo approssimato di una riga (ascendenti + discendenti del corpo)."""
    width = item.width if item.width > 0 else max(len(item.text), 1) * item.size * 0.5
    top = item.baseline_y - item.size * ASCENT_RATIO
    bottom = item.baseline_y + item.size * DESCENT_RATIO
    return Rect(item.x, top, item.x + width, bottom)


def check_page_geometry(
    page_number: int,
    items: Sequence[PositionedText],
    *,
    page_width: float,
    page_height: float,
) -> list[QAIssue]:
    """Issue geometriche della pagina, in ordine: prima le sovrapposizioni, poi il clipping."""
    visible = [item for item in items if item.text.strip()]
    issues = _overlaps(page_number, visible)
    issues.extend(_clipped(page_number, visible, page_width, page_height))
    return issues[:MAX_ISSUES_PER_PAGE]


def _overlaps(page_number: int, items: Iterable[PositionedText]) -> list[QAIssue]:
    boxes = [(item.block_id, run_box(item)) for item in items]
    issues: list[QAIssue] = []
    for (block_a, box_a), (block_b, box_b) in combinations(boxes, 2):
        if block_a == block_b:
            continue
        overlap = box_a.intersection(box_b)
        if overlap is None or overlap.height < MIN_VERTICAL_OVERLAP:
            continue
        smallest = min(box_a.area, box_b.area)
        if smallest <= 0 or overlap.area < MIN_OVERLAP_AREA:
            continue
        if overlap.area / smallest < MIN_OVERLAP_RATIO:
            continue
        issues.append(
            QAIssue(
                page=page_number,
                kind=IssueKind.TEXT_OVERLAP,
                block=block_a,
                detail=f"si sovrappone a {block_b} per {overlap.area:.1f} pt²",
            )
        )
    return issues


def _clipped(
    page_number: int,
    items: Iterable[PositionedText],
    page_width: float,
    page_height: float,
) -> list[QAIssue]:
    issues: list[QAIssue] = []
    for item in items:
        box = run_box(item)
        problems: list[str] = []
        if box.x1 > page_width + PAGE_TOLERANCE:
            problems.append(f"oltre il margine destro ({box.x1:.0f} > {page_width:.0f})")
        if box.x0 < -PAGE_TOLERANCE:
            problems.append(f"oltre il margine sinistro ({box.x0:.0f})")
        if box.y1 > page_height + PAGE_TOLERANCE:
            problems.append(f"sotto il bordo pagina ({box.y1:.0f} > {page_height:.0f})")
        if box.y0 < -PAGE_TOLERANCE:
            problems.append(f"sopra il bordo pagina ({box.y0:.0f})")
        if problems:
            issues.append(
                QAIssue(
                    page=page_number,
                    kind=IssueKind.CLIPPED,
                    block=item.block_id,
                    detail="; ".join(problems),
                )
            )
    return issues
