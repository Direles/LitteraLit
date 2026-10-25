"""Painter dei blocchi di prosa (M9).

Un blocco di prosa: una traduzione, un'area, un corpo target. Il painter sceglie il corpo
(``layout.fitter``), eventualmente chiede una versione più corta (``ShortenerPort``),
calcola le baseline e produce righe + issue. Non tocca il canvas: il disegno è del
renderer, così il painter è testabile senza PDF.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from pdfbook.domain.models import IssueKind, PageLayout, QAIssue, Rect, TextBlock
from pdfbook.domain.ports import FontResolverPort, ShortenerPort
from pdfbook.layout.aligner import alignments_for
from pdfbook.layout.fitter import FitResult, estimate_max_chars, fit_text
from pdfbook.layout.hyphenation import Hyphenation

from .canvas import TextRun
from .runs import baselines_for, prose_runs

__all__ = ["MIN_TEXT_TO_SHORTEN", "RETRANSLATE_THRESHOLD", "BlockPainter", "BlockResult"]

RETRANSLATE_THRESHOLD = 0.75
MIN_TEXT_TO_SHORTEN = 40


@dataclass
class BlockResult:
    """Esito del painter su un blocco."""

    runs: list[TextRun] = field(default_factory=list)
    y_end: float = 0.0
    issues: list[QAIssue] = field(default_factory=list)
    perfect: int = 0
    font_reduced: int = 0
    retranslated: int = 0


class BlockPainter:
    """Dipinge un blocco di prosa: fit, ritraduzione compressa, baseline, righe."""

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
        if missing_policy not in ("skip", "keep"):
            raise ValueError("missing_policy deve essere 'skip' o 'keep'")
        self.resolver = resolver
        self.hyphenation = hyphenation
        self.shortener = shortener
        self.missing_policy = missing_policy
        self.overflow_policy = overflow_policy
        self.retranslate_threshold = retranslate_threshold

    # ---------- API ----------

    def paint(
        self,
        block: TextBlock,
        page: PageLayout,
        translations: Mapping[str, str],
        shift: float,
        *,
        key: str | None = None,
        cell: bool = False,
    ) -> BlockResult:
        """Dipinge il blocco; ``key`` permette di usare una chiave diversa da ``block.id``."""
        result = BlockResult(y_end=block.bbox.y1 + shift)
        text = self._translation(translations, key or block.id, block.text, page.number, result)
        if not text:
            return result
        target = block.primary_span.size
        bounds = Rect(block.bbox.x0, block.bbox.y0 + shift, block.bbox.x1, block.bbox.y1 + shift)
        fit, text, shortened = self._fit_block(text, block, page, bounds, target, cell=cell)
        self._record_fit(block, fit, target, shortened, page.number, result, cell=cell)

        baselines = baselines_for(block, fit.size, len(fit.lines), shift)
        alignments = alignments_for(block, page.width, len(fit.lines))
        result.runs = prose_runs(
            block,
            lines=fit.lines,
            size=fit.size,
            baselines=baselines,
            alignments=alignments,
            resolver=self.resolver,
        )
        last = baselines[-1] if baselines else bounds.y0
        result.y_end = max(result.y_end, last + fit.size * 0.20)
        return result

    # ---------- fit ----------

    def _fit_block(
        self,
        text: str,
        block: TextBlock,
        page: PageLayout,
        bounds: Rect,
        target: float,
        *,
        cell: bool = False,
    ) -> tuple[FitResult, str, bool]:
        fit = self.fit(
            text, block, page, bounds, target,
            overflow_policy="shrink" if cell else None,
        )
        if fit.size >= target * self.retranslate_threshold or len(text) <= MIN_TEXT_TO_SHORTEN:
            return fit, text, False
        if self.shortener is None:
            return fit, text, False
        budget = estimate_max_chars(
            self._measure(block),
            size=target,
            max_width=bounds.width,
            num_lines=block.line_count,
            sample=text,
        )
        short = self.shortener.shorten(block.text, text, budget)
        if not short or len(short) >= len(text):
            return fit, text, False
        return self.fit(short, block, page, bounds, target), short, True

    def fit(
        self,
        text: str,
        block: TextBlock,
        page: PageLayout,
        bounds: Rect,
        target: float,
        max_width: float | None = None,
        overflow_policy: str | None = None,
    ) -> FitResult:
        """Fitting su un blocco (o su una colonna, con ``max_width`` esplicito)."""
        width = max_width if max_width is not None else self.usable_width(bounds, page)
        return fit_text(
            text,
            measure=self._measure(block),
            max_width=width,
            target_size=target,
            max_lines=block.line_count,
            bounds=bounds,
            obstacles=page.image_boxes,
            hyphenation=self.hyphenation,
            overflow_policy=overflow_policy or self.overflow_policy,
        )

    @staticmethod
    def usable_width(bounds: Rect, page: PageLayout) -> float:
        """Larghezza del blocco, mai oltre il margine destro della pagina."""
        available = page.width - bounds.x0 - 10.0
        return max(min(bounds.width, available), 1.0)

    def _measure(self, block: TextBlock) -> Callable[[str, float], float]:
        font_name = block.primary_span.font_name

        def measure(text: str, size: float) -> float:
            return float(self.resolver.text_length(text, font_name, size))

        return measure

    # ---------- issue ----------

    def _translation(
        self,
        translations: Mapping[str, str],
        key: str,
        original: str,
        page_number: int,
        result: BlockResult,
    ) -> str | None:
        text = translations.get(key)
        if text and text.strip():
            return text
        result.issues.append(
            QAIssue(
                page=page_number,
                kind=IssueKind.UNTRANSLATED_UNRESOLVED,
                block=key,
                detail="traduzione assente: blocco non reso"
                if self.missing_policy == "skip"
                else "traduzione assente: reso l'originale",
            )
        )
        return original if self.missing_policy == "keep" else None

    def _record_fit(
        self,
        block: TextBlock,
        fit: FitResult,
        target: float,
        shortened: bool,
        page_number: int,
        result: BlockResult,
        *,
        cell: bool = False,
    ) -> None:
        if fit.fits:
            result.perfect += 1
        else:
            result.issues.append(
                QAIssue(
                    page=page_number,
                    kind=IssueKind.TABLE_MISALIGNED if cell else IssueKind.CLIPPED,
                    block=block.id,
                    detail=(
                        f"cella su {len(fit.lines)} righe (prevista {block.line_count})"
                        if cell
                        else f"{len(fit.lines)} righe > {block.line_count} previste"
                    ),
                )
            )
        if fit.reduced_compared_to(target):
            result.font_reduced += 1
            result.issues.append(
                QAIssue(
                    page=page_number,
                    kind=IssueKind.FONT_REDUCED,
                    block=block.id,
                    detail=f"{target:.1f}pt -> {fit.size:.1f}pt",
                )
            )
        if shortened:
            result.retranslated += 1
            result.issues.append(
                QAIssue(
                    page=page_number,
                    kind=IssueKind.RETRANSLATED,
                    block=block.id,
                    detail="traduzione accorciata su richiesta del layout",
                )
            )
