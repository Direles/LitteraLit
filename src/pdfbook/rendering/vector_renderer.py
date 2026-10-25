"""Orchestrazione del rendering di pagina (M9).

Responsabilità: classificare i blocchi, redigere l'originale, delegare ogni blocco al
painter giusto (prosa o strutturato), propagare lo shift verticale e raccogliere
issue/contatori. Niente aritmetica tipografica (``runs``) e niente fitting (``layout``).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

from pdfbook.domain.models import IssueKind, PageLayout, QAIssue, Rect
from pdfbook.domain.ports import FontResolverPort, ShortenerPort
from pdfbook.layout.hyphenation import Hyphenation
from pdfbook.layout.segmentation import classify_block, is_structured_block
from pdfbook.qa.checks_geometry import check_page_geometry

from .canvas import PageCanvas
from .painter import RETRANSLATE_THRESHOLD, BlockPainter, BlockResult
from .runs import shift_for
from .structured_painter import StructuredPainter

__all__ = ["SHIFT_TOLERANCE", "PageRenderResult", "VectorRenderer"]

log = logging.getLogger(__name__)

SHIFT_TOLERANCE = 0.5


@dataclass
class PageRenderResult:
    """Esito del rendering di una pagina."""

    issues: list[QAIssue] = field(default_factory=list)
    blocks: int = 0
    perfect: int = 0
    font_reduced: int = 0
    shifted: int = 0
    retranslated: int = 0
    not_drawn: int = 0

    def merge(self, block: BlockResult) -> None:
        self.issues.extend(block.issues)
        self.perfect += block.perfect
        self.font_reduced += block.font_reduced
        self.retranslated += block.retranslated


class VectorRenderer:
    """Compone una pagina tradotta su un ``PageCanvas``."""

    def __init__(
        self,
        resolver: FontResolverPort,
        *,
        hyphenation: Hyphenation | None = None,
        shortener: ShortenerPort | None = None,
        missing_policy: str = "skip",
        overflow_policy: str = "keep_size",
        retranslate_threshold: float = RETRANSLATE_THRESHOLD,
    ) -> None:
        shared = dict(
            hyphenation=hyphenation,
            shortener=shortener,
            missing_policy=missing_policy,
            overflow_policy=overflow_policy,
            retranslate_threshold=retranslate_threshold,
        )
        self.prose = BlockPainter(resolver, **shared)
        self.structured = StructuredPainter(resolver, **shared)

    def render_page(
        self,
        canvas: PageCanvas,
        page: PageLayout,
        translations: Mapping[str, str],
    ) -> PageRenderResult:
        """Redige l'originale, dipinge i blocchi, disegna e riporta i fallimenti."""
        result = PageRenderResult()
        blocks = sorted(
            (classify_block(block) for block in page.blocks),
            key=lambda block: block.bbox.y0,
        )
        for block in blocks:
            canvas.redact(block.bbox)
        canvas.apply_redactions()

        placed: list[tuple[Rect, float]] = []
        collected: list = []
        for block in blocks:
            shift = shift_for(block.bbox, placed)
            if shift > SHIFT_TOLERANCE:
                result.shifted += 1
            painter = self.structured if is_structured_block(block) else self.prose
            painted = painter.paint(block, page, translations, shift)
            result.blocks += 1
            result.merge(painted)
            collected.extend(painted.runs)
            self._draw(canvas, page, painted.runs, result)
            placed.append((block.bbox, painted.y_end))
        result.issues.extend(
            check_page_geometry(
                page.number,
                collected,
                page_width=page.width,
                page_height=page.height,
            )
        )
        return result

    @staticmethod
    def _draw(canvas: PageCanvas, page: PageLayout, runs: list, result: PageRenderResult) -> None:
        if not runs:
            return
        for run in canvas.draw(runs):
            result.not_drawn += 1
            result.issues.append(
                QAIssue(
                    page=page.number,
                    kind=IssueKind.TEXT_MISSING,
                    detail=f"riga non disegnata: {run.text[:40]!r}",
                )
            )
