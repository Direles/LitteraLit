"""Geometria e costruzione dei ``TextRun`` (M9).

Funzioni pure: nessuno stato, nessun effetto collaterale. Ricevono un resolver per le
metriche e restituiscono righe pronte da disegnare. Tutta l'aritmetica di posizionamento
sta qui, così il painter non la mescola con la logica di fitting.
"""

from __future__ import annotations

from collections.abc import Sequence

from pdfbook.domain.models import Line, Rect, TextBlock
from pdfbook.domain.ports import FontResolverPort

from .canvas import TextRun
from .colors import rgb_from_int

__all__ = [
    "baselines_for",
    "column_runs",
    "column_x",
    "extra_height",
    "prose_runs",
    "shift_for",
    "tail",
    "x_for",
]


def baselines_for(block: TextBlock, fit_size: float, line_count: int, shift: float) -> list[float]:
    """Baseline da usare: quelle originali se bastano, altrimenti interlinea calcolata."""
    if line_count <= block.line_count:
        return [line.origin_y + shift for line in block.lines[:line_count]]
    first = block.lines[0].origin_y + shift
    return [first + index * fit_size * 1.25 for index in range(line_count)]


def prose_runs(
    block: TextBlock,
    *,
    lines: Sequence[str],
    size: float,
    baselines: Sequence[float],
    alignments: Sequence[str],
    resolver: FontResolverPort,
) -> list[TextRun]:
    """Righe di un blocco di prosa, con allineamento e colore dello span principale."""
    span = block.primary_span
    font = resolver.resolve(span.font_name)
    color = rgb_from_int(span.color)
    runs: list[TextRun] = []
    for piece, baseline, align in zip(lines, baselines, alignments, strict=False):
        if not piece.strip():
            continue
        width = resolver.text_length(piece, span.font_name, size)
        runs.append(
            TextRun(
                x=x_for(block.bbox.x0, block.bbox.width, width, align),
                baseline_y=baseline,
                text=piece,
                font=font,
                size=size,
                color=color,
                width=width,
                block_id=block.id,
            )
        )
    return runs


def column_runs(
    block: TextBlock,
    line: Line,
    *,
    lines: Sequence[str],
    size: float,
    baseline_y: float,
    max_width: float,
    align: str,
    resolver: FontResolverPort,
) -> list[TextRun]:
    """Righe di una colonna di un blocco strutturato (indice, intestazione affiancata)."""
    span = line.primary_span
    font = resolver.resolve(span.font_name)
    color = rgb_from_int(span.color)
    runs: list[TextRun] = []
    for offset, piece in enumerate(lines):
        if not piece.strip():
            continue
        width = resolver.text_length(piece, span.font_name, size)
        runs.append(
            TextRun(
                x=column_x(line.bbox.x0, block.bbox.x1, max_width, width, align),
                baseline_y=baseline_y + offset * size * 1.25,
                text=piece,
                font=font,
                size=size,
                color=color,
                width=width,
                block_id=block.id,
            )
        )
    return runs


def x_for(x0: float, max_width: float, width: float, align: str) -> float:
    """Coordinata X della riga nel blocco."""
    if align == "center":
        return x0 + (max_width - width) / 2
    if align == "right":
        return x0 + max_width - width
    return x0


def column_x(column_x0: float, column_x1: float, max_width: float, width: float, align: str) -> float:
    """Coordinata X di una colonna: parte dalla propria ``x0``, non da quella del blocco."""
    if align == "center":
        return column_x0 + (max_width - width) / 2
    if align == "right":
        return max(column_x1 - width - 2.0, column_x0)
    return column_x0


def shift_for(box: Rect, placed: Sequence[tuple[Rect, float]]) -> float:
    """Spostamento verticale dovuto ai blocchi precedenti che si sovrappongono in X."""
    shift = 0.0
    for previous, y_end in placed:
        if previous.x0 < box.x1 and box.x0 < previous.x1:
            shift = max(shift, y_end - previous.y1)
    return max(shift, 0.0)


def extra_height(runs: Sequence[TextRun]) -> float:
    """Altezza aggiuntiva di una colonna andata su più righe."""
    if len(runs) < 2:
        return 0.0
    size = max(run.size for run in runs)
    return (len(runs) - 1) * size * 1.25


def tail(runs: Sequence[TextRun]) -> float:
    """Spazio da riservare sotto l'ultima baseline (discendenti)."""
    return max(run.size for run in runs) * 0.30 if runs else 0.0
