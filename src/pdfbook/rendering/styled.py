"""Disegno di un blocco con stili inline (Fase 1.2).

Estratto dal painter di prosa perché è una strategia a sé: fit sul font dominante,
a capo con le metriche di **ogni** parola, disegno parola per parola con il font dello
stile. Il risultato sono ``TextRun`` normali: il renderer non sa che esistono gli stili.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from pdfbook.domain.models import IssueKind, PageLayout, QAIssue, Rect, TextBlock
from pdfbook.domain.ports import FontResolverPort
from pdfbook.fonts.platform_fonts import classify
from pdfbook.layout.aligner import alignments_for
from pdfbook.layout.fitter import MIN_FONT_FRACTION, MIN_FONT_SIZE, SIZE_STEP
from pdfbook.layout.styles import StyledPiece, parse_tagged, wrap_pieces

from .canvas import TextRun
from .colors import rgb_from_int
from .runs import baselines_for, x_for

__all__ = ["paint_styled"]


def paint_styled(
    *,
    block: TextBlock,
    page: PageLayout,
    marked_text: str,
    shift: float,
    result,
    resolver: FontResolverPort,
    usable_width: Callable[[Rect, PageLayout], float],
) -> None:
    """Riempie ``result`` con i run stilizzati e le issue del caso."""
    pieces = parse_tagged(marked_text)
    if not pieces:
        return
    names = style_font_names(block)
    measure = styled_measure(resolver, names)
    bounds = Rect(block.bbox.x0, block.bbox.y0 + shift, block.bbox.x1, block.bbox.y1 + shift)
    width = usable_width(bounds, page)
    target = block.primary_span.size
    size, chosen = _fit_styled(pieces, measure, width, target, block.line_count)
    if size < target - 0.25:
        result.font_reduced += 1
        result.issues.append(
            QAIssue(
                page=page.number,
                kind=IssueKind.FONT_REDUCED,
                block=block.id,
                detail=f"{target:.1f}pt -> {size:.1f}pt",
            )
        )
    else:
        result.perfect += 1
    if len(chosen) > max(block.line_count, 1):
        result.issues.append(
            QAIssue(
                page=page.number,
                kind=IssueKind.CLIPPED,
                block=block.id,
                detail=f"testo con stili su {len(chosen)} righe > {block.line_count}",
            )
        )
    result.runs = _runs(block, page, chosen, measure, names, resolver, size, shift, width)
    baselines = baselines_for(block, size, len(chosen), shift)
    last = baselines[-1] if baselines else bounds.y0
    result.y_end = max(result.y_end, last + size * 0.20)


def style_font_names(block: TextBlock) -> dict[tuple[bool, bool], str]:
    """Nome del font originale per ogni combinazione di stile presente nel blocco."""
    names: dict[tuple[bool, bool], str] = {(False, False): block.primary_span.font_name}
    for line in block.lines:
        for span in line.spans:
            _, bold, italic = classify(span.font_name)
            names.setdefault((bold, italic), span.font_name)
    return names


def styled_measure(
    resolver: FontResolverPort, names: Mapping[tuple[bool, bool], str]
) -> Callable[[str, bool, bool, float], float]:
    def measure(text: str, bold: bool, italic: bool, size: float) -> float:
        font_name = names.get((bold, italic), names[(False, False)])
        return float(resolver.text_length(text, font_name, size))

    return measure


def _fit_styled(
    pieces: list[StyledPiece],
    measure: Callable[[str, bool, bool, float], float],
    width: float,
    target: float,
    max_lines: int,
) -> tuple[float, list[list[StyledPiece]]]:
    floor = max(target * MIN_FONT_FRACTION, MIN_FONT_SIZE)
    size = target
    lines = wrap_pieces(pieces, measure=measure, size=size, max_width=width)
    while size > floor and len(lines) > max(max_lines, 1):
        size -= SIZE_STEP
        lines = wrap_pieces(pieces, measure=measure, size=size, max_width=width)
    return size, lines


def _runs(
    block: TextBlock,
    page: PageLayout,
    lines: list[list[StyledPiece]],
    measure: Callable[[str, bool, bool, float], float],
    names: Mapping[tuple[bool, bool], str],
    resolver: FontResolverPort,
    size: float,
    shift: float,
    width: float,
) -> list[TextRun]:
    baselines = baselines_for(block, size, len(lines), shift)
    alignments = alignments_for(block, page.width, len(lines))
    color = rgb_from_int(block.primary_span.color)
    space = measure(" ", False, False, size)
    runs: list[TextRun] = []
    for index, line_pieces in enumerate(lines):
        line_width = sum(
            measure(piece.text, piece.bold, piece.italic, size) for piece in line_pieces
        ) + space * max(len(line_pieces) - 1, 0)
        x = x_for(block.bbox.x0, width, line_width, alignments[index])
        for position, piece in enumerate(line_pieces):
            if position:
                x += space
            piece_width = measure(piece.text, piece.bold, piece.italic, size)
            font_name = names.get((piece.bold, piece.italic), names[(False, False)])
            runs.append(
                TextRun(
                    x=x,
                    baseline_y=baselines[index],
                    text=piece.text,
                    font=resolver.resolve(font_name),
                    size=size,
                    color=color,
                    width=piece_width,
                    block_id=block.id,
                )
            )
            x += piece_width
    return runs
