"""Ordine di lettura multi-colonna (Fase 2.5).

Un PDF a due colonne spesso esce dall'estrazione come blocchi **intercalati** (riga della
colonna sinistra, riga della destra, poi di nuovo sinistra): tradurre quell'ordine produce
frasi che saltano da una colonna all'altra.

Qui si ricostruisce l'ordine vero: colonna sinistra dall'alto in basso, poi la destra.
Regola di prudenza: si riordina **solo** quando il gutter è netto e nessun blocco a tutta
larghezza cade dentro la fascia delle colonne. In tutti gli altri casi si restituisce
l'ordine originale — meglio non toccare nulla che inventare una lettura sbagliata.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from pdfbook.domain.models import PageLayout, TextBlock

__all__ = [
    "GUTTER_MIN",
    "MIN_BLOCKS_PER_COLUMN",
    "WIDE_SHARE",
    "Column",
    "apply_reading_order",
    "detect_columns",
    "reading_order",
]

#: Larghezza minima del corridoio fra due colonne, in punti.
GUTTER_MIN = 10.0
#: Ogni colonna deve avere almeno questo numero di blocchi per essere credibile.
MIN_BLOCKS_PER_COLUMN = 2
#: Un blocco più largo di questa frazione della pagina è "a tutta larghezza".
WIDE_SHARE = 0.72


@dataclass(frozen=True)
class Column:
    """Fascia verticale di blocchi, con gli id in ordine di lettura."""

    x0: float
    x1: float
    blocks: tuple[str, ...]


def detect_columns(blocks: Sequence[TextBlock], page_width: float) -> list[Column]:
    """Riconosce due colonne affiancate; lista vuota se la pagina non è a colonne."""
    narrow = [block for block in blocks if _width(block) < page_width * WIDE_SHARE]
    if len(narrow) < MIN_BLOCKS_PER_COLUMN * 2:
        return []
    gutter = _widest_gutter(narrow)
    if gutter is None:
        return []
    left_edge, right_edge = gutter
    left = [block for block in narrow if block.bbox.x1 <= left_edge + 0.5]
    right = [block for block in narrow if block.bbox.x0 >= right_edge - 0.5]
    if len(left) < MIN_BLOCKS_PER_COLUMN or len(right) < MIN_BLOCKS_PER_COLUMN:
        return []
    if len(left) + len(right) != len(narrow):
        return []
    return [
        Column(min(b.bbox.x0 for b in left), max(b.bbox.x1 for b in left), _ids(left)),
        Column(min(b.bbox.x0 for b in right), max(b.bbox.x1 for b in right), _ids(right)),
    ]


def reading_order(blocks: Sequence[TextBlock], page_width: float) -> list[str]:
    """Id dei blocchi nell'ordine di lettura; ordine originale se non è a colonne."""
    columns = detect_columns(blocks, page_width)
    original = [block.id for block in blocks]
    if not columns:
        return original
    left, right = columns
    col_blocks = set(left.blocks) | set(right.blocks)
    wide = [block for block in blocks if block.id not in col_blocks]
    top = min(_top(block) for block in blocks if block.id in col_blocks)
    bottom = max(_bottom(block) for block in blocks if block.id in col_blocks)
    if any(top < _center(block) < bottom for block in wide):
        return original
    before = [block.id for block in wide if _center(block) <= top]
    after = [block.id for block in wide if _center(block) >= bottom]
    if len(before) + len(after) != len(wide):
        return original
    return before + list(left.blocks) + list(right.blocks) + after


def apply_reading_order(page: PageLayout) -> PageLayout:
    """Restituisce la pagina con i blocchi riordinati (id e geometria invariati)."""
    order = reading_order(page.blocks, page.width)
    if order == [block.id for block in page.blocks]:
        return page
    by_id = {block.id: block for block in page.blocks}
    return replace(page, blocks=[by_id[block_id] for block_id in order])


def _widest_gutter(blocks: Sequence[TextBlock]) -> tuple[float, float] | None:
    spans = sorted((block.bbox.x0, block.bbox.x1) for block in blocks)
    merged: list[list[float]] = []
    for x0, x1 in spans:
        if merged and x0 <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], x1)
        else:
            merged.append([x0, x1])
    if len(merged) != 2:
        return None
    left_edge, right_edge = merged[0][1], merged[1][0]
    if right_edge - left_edge < GUTTER_MIN:
        return None
    return left_edge, right_edge



def _ids(blocks: Sequence[TextBlock]) -> tuple[str, ...]:
    return tuple(block.id for block in sorted(blocks, key=lambda b: (b.bbox.y0, b.bbox.x0)))


def _width(block: TextBlock) -> float:
    return max(block.bbox.x1 - block.bbox.x0, 0.0)


def _top(block: TextBlock) -> float:
    return block.bbox.y0


def _bottom(block: TextBlock) -> float:
    return block.bbox.y1


def _center(block: TextBlock) -> float:
    return (block.bbox.y0 + block.bbox.y1) / 2

