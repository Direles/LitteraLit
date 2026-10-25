"""Painter dei blocchi strutturati (M9): indici e intestazioni a colonne.

Un blocco strutturato si dipinge **riga per riga**: ogni colonna mantiene la propria
``x0`` e la propria larghezza, così un'etichetta corta e un titolo affiancato non si
sovrappongono dopo la traduzione. Riutilizza fitting e gestione delle issue del painter
di prosa, cambiando solo la geometria.
"""

from __future__ import annotations

from collections.abc import Mapping

from pdfbook.domain.models import IssueKind, Line, PageLayout, QAIssue, Rect, TextBlock
from pdfbook.layout.aligner import line_alignment
from pdfbook.layout.segmentation import group_rows

from .painter import BlockPainter, BlockResult
from .runs import column_runs, extra_height, tail

__all__ = ["COLUMN_GAP", "MIN_COLUMN_WIDTH", "StructuredPainter"]

COLUMN_GAP = 4.0
MIN_COLUMN_WIDTH = 30.0


class StructuredPainter(BlockPainter):
    """Dipinge un blocco riga per riga (indice, intestazione a colonne)."""

    def paint(  # type: ignore[override]
        self,
        block: TextBlock,
        page: PageLayout,
        translations: Mapping[str, str],
        shift: float,
        *,
        cell: bool = False,
    ) -> BlockResult:
        result = BlockResult(y_end=block.bbox.y1 + shift)
        index_of = {id(line): index for index, line in enumerate(block.lines)}
        internal = 0.0
        all_fit = True
        for row in group_rows(block.lines):
            row_extra = 0.0
            for line in row:
                baseline = line.origin_y + shift + internal
                runs, fits = self._column(
                    block, line, index_of[id(line)], baseline, translations, page, result
                )
                all_fit = all_fit and fits
                result.runs.extend(runs)
                if runs:
                    row_extra = max(row_extra, extra_height(runs))
                    result.y_end = max(result.y_end, max(run.baseline_y for run in runs) + tail(runs))
            internal += row_extra
        result.perfect = 1 if all_fit and result.runs else 0
        return result

    def _column(
        self,
        block: TextBlock,
        line: Line,
        index: int,
        baseline_y: float,
        translations: Mapping[str, str],
        page: PageLayout,
        result: BlockResult,
    ) -> tuple[list, bool]:
        key = f"{block.id}_l{index}"
        text = self._translation(translations, key, line.text, page.number, result)
        if not text:
            return [], False
        span = line.primary_span
        target = span.size or block.primary_span.size
        max_width = max(block.bbox.x1 - line.bbox.x0 - COLUMN_GAP, MIN_COLUMN_WIDTH)
        bounds = Rect(
            line.bbox.x0, baseline_y - target, line.bbox.x0 + max_width, baseline_y + target
        )
        fit = self.fit(text, block, page, bounds, target, max_width=max_width)
        if not fit.fits:
            result.issues.append(
                QAIssue(
                    page=page.number,
                    kind=IssueKind.CLIPPED,
                    block=key,
                    detail=f"colonna su {len(fit.lines)} righe (prevista 1)",
                )
            )
        if fit.reduced_compared_to(target):
            result.font_reduced += 1
            result.issues.append(
                QAIssue(
                    page=page.number,
                    kind=IssueKind.FONT_REDUCED,
                    block=key,
                    detail=f"{target:.1f}pt -> {fit.size:.1f}pt",
                )
            )
        return column_runs(
            block,
            line,
            lines=fit.lines,
            size=fit.size,
            baseline_y=baseline_y,
            max_width=max_width,
            align=line_alignment(line, block),
            resolver=self.resolver,
        ), fit.fits
