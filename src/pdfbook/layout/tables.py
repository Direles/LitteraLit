"""Riconoscimento di tabelle dalla geometria del testo (Fase 2.3).

Non ricostruiamo la griglia vettoriale: usiamo un segnale più semplice e robusto — celle
allineate su più righe consecutive con le stesse colonne. È sufficiente per il caso reale
dei libri tecnici, dove ogni cella è un blocco di testo autonomo.

Gli errori da evitare sono due: prendere per tabella un layout a due colonne (le colonne di
testo hanno blocchi alti e non allineati riga per riga) e perdere tabelle senza bordi.
Per questo le soglie sono conservative: almeno 3 righe, almeno 2 colonne, celle corte.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pdfbook.domain.models import BlockKind, PageLayout, Rect, TextBlock

__all__ = ["MIN_COLS", "MIN_ROWS", "Table", "detect_tables", "mark_tables"]

ROW_TOL = 2.0
COL_TOL = 4.0
MIN_ROWS = 3
MIN_COLS = 2
MAX_ROW_GAP_FACTOR = 3.0
MAX_CELL_CHARS = 200
_MAX_WIDTH_SHARE = 0.95
_CANDIDATE_KINDS = {BlockKind.PARAGRAPH, BlockKind.UNKNOWN, BlockKind.TABLE_CELL}


@dataclass(frozen=True)
class Table:
    """Tabella riconosciuta: bbox complessiva e identificativi delle celle per riga."""

    bbox: Rect
    rows: tuple[tuple[str, ...], ...]

    @property
    def column_count(self) -> int:
        return len(self.rows[0]) if self.rows else 0

    @property
    def cells(self) -> tuple[str, ...]:
        return tuple(cell for row in self.rows for cell in row)


def detect_tables(page: PageLayout) -> list[Table]:
    """Tabelle della pagina, in ordine dall'alto."""
    candidates = [block for block in page.blocks if _is_candidate(block, page)]
    rows = _rows(candidates)
    tables: list[Table] = []
    run: list[list[TextBlock]] = []
    for row in rows:
        if len(row) < MIN_COLS:
            tables.extend(_close(run))
            run = []
            continue
        if run and (not _aligned(run[-1], row) or _gap(run[-1], row)):
            tables.extend(_close(run))
            run = [row]
        else:
            run.append(row)
    tables.extend(_close(run))
    return tables


def mark_tables(page: PageLayout) -> PageLayout:
    """Restituisce la pagina con le celle marcate come ``TABLE_CELL``."""
    tables = detect_tables(page)
    if not tables:
        return page
    cells = {block_id for table in tables for block_id in table.cells}
    page.blocks = [
        block if block.id not in cells else _as_cell(block) for block in page.blocks
    ]
    return page


def _close(run: Sequence[Sequence[TextBlock]]) -> list[Table]:
    if len(run) < MIN_ROWS:
        return []
    rows = tuple(tuple(block.id for block in row) for row in run)
    boxes = [block.bbox for row in run for block in row]
    bbox = Rect(
        min(box.x0 for box in boxes),
        min(box.y0 for box in boxes),
        max(box.x1 for box in boxes),
        max(box.y1 for box in boxes),
    )
    return [Table(bbox=bbox, rows=rows)]


def _rows(blocks: Sequence[TextBlock]) -> list[list[TextBlock]]:
    rows: list[list[TextBlock]] = []
    for block in sorted(blocks, key=lambda item: (item.bbox.y0, item.bbox.x0)):
        for row in rows:
            if abs(row[0].bbox.y0 - block.bbox.y0) <= ROW_TOL:
                row.append(block)
                break
        else:
            rows.append([block])
    for row in rows:
        row.sort(key=lambda item: item.bbox.x0)
    rows.sort(key=lambda row: row[0].bbox.y0)
    return rows


def _aligned(previous: Sequence[TextBlock], current: Sequence[TextBlock]) -> bool:
    if len(previous) != len(current):
        return False
    return all(
        abs(left.bbox.x0 - right.bbox.x0) <= COL_TOL
        for left, right in zip(previous, current, strict=True)
    )


def _gap(previous: Sequence[TextBlock], current: Sequence[TextBlock]) -> bool:
    """Un salto verticale ampio separa due tabelle distinte."""
    height = max(block.bbox.height for block in previous) or 1.0
    distance = current[0].bbox.y0 - previous[0].bbox.y0
    return distance > height * MAX_ROW_GAP_FACTOR


def _is_candidate(block: TextBlock, page: PageLayout) -> bool:
    text = block.text.strip()
    if not text or len(text) > MAX_CELL_CHARS:
        return False
    if block.kind not in _CANDIDATE_KINDS:
        return False
    if block.line_count > 1:
        return False  # una cella è tipicamente una riga; i paragrafi no
    return block.bbox.width <= page.width * _MAX_WIDTH_SHARE


def _as_cell(block: TextBlock) -> TextBlock:
    if block.kind is BlockKind.TABLE_CELL:
        return block
    from dataclasses import replace

    return replace(block, kind=BlockKind.TABLE_CELL)
