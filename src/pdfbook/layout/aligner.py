"""Allineamento orizzontale delle righe (M7).

L'italiano è più lungo dell'inglese: senza riallineare, un titolo centrato tradotto
diventa un paragrafo spostato a sinistra. Le soglie sono esplicite e testate, non
``if`` sparsi nel renderer.
"""

from __future__ import annotations

from collections.abc import Sequence

from pdfbook.domain.models import Line, TextBlock

__all__ = [
    "CENTER_TOLERANCE_RATIO",
    "MIN_TOLERANCE_POINTS",
    "SINGLE_LINE_CENTER_POINTS",
    "alignments_for",
    "line_alignment",
    "single_line_alignment",
]

# Tolleranze (in frazione della larghezza del blocco, con minimo in punti).
CENTER_TOLERANCE_RATIO = 0.05
MIN_TOLERANCE_POINTS = 5.0
# Per i blocchi a riga singola si confronta con il centro pagina.
SINGLE_LINE_CENTER_POINTS = 15.0
SINGLE_LINE_MAX_WIDTH_RATIO = 0.8
RIGHT_EDGE_POINTS = 50.0


def line_alignment(line: Line, block: TextBlock) -> str:
    """Allineamento della riga rispetto al **blocco**: ``left``, ``center`` o ``right``."""
    block_width = block.bbox.width
    line_width = line.bbox.width
    if block_width <= 0 or line_width <= 0:
        return "left"
    if line_width >= 0.95 * block_width:
        return "left"  # riga "piena": nessuna informazione utile sull'allineamento
    tolerance = max(CENTER_TOLERANCE_RATIO * block_width, MIN_TOLERANCE_POINTS)
    line_center = line.bbox.x0 + line_width / 2
    block_center = block.bbox.x0 + block_width / 2
    if abs(line_center - block_center) < tolerance:
        return "center"
    if abs(line.bbox.x1 - block.bbox.x1) < tolerance:
        return "right"
    return "left"


def single_line_alignment(block: TextBlock, page_width: float) -> str:
    """Allineamento di un blocco a riga singola, confrontato con il centro **pagina**."""
    if page_width <= 0:
        return "left"
    block_center = block.bbox.x0 + block.bbox.width / 2
    page_center = page_width / 2
    if (
        abs(block_center - page_center) < SINGLE_LINE_CENTER_POINTS
        and block.bbox.width < SINGLE_LINE_MAX_WIDTH_RATIO * page_width
    ):
        return "center"
    if (
        abs(block.bbox.x1 - page_width) < RIGHT_EDGE_POINTS
        and block.bbox.x0 > page_center
    ):
        return "right"
    return "left"


def alignments_for(block: TextBlock, page_width: float, line_count: int) -> tuple[str, ...]:
    """Allineamento per ognuna delle ``line_count`` righe tradotte.

    - blocco a riga singola: lo stesso allineamento per tutte le righe prodotte;
    - blocco multi-riga: allineamento della riga originale corrispondente, poi l'ultimo noto.
    """
    if line_count <= 0:
        return ()
    if block.line_count == 1:
        return (single_line_alignment(block, page_width),) * line_count
    original: Sequence[Line] = block.lines
    result: list[str] = []
    for index in range(line_count):
        if index < len(original):
            result.append(line_alignment(original[index], block))
        else:
            result.append(result[-1] if result else "left")
    return tuple(result)
