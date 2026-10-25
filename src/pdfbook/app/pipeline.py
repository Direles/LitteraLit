"""Pipeline di documento (M11): PDF → pagine → traduzione → rendering → QA.

Il job è l'unico punto che conosce il *flusso*: legge le pagine, costruisce il batch di
traduzione, delega rendering e QA, salva e chiude. Non contiene né HTTP né disegno.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from pdfbook.config.settings import AppSettings
from pdfbook.domain.models import IssueKind, PageLayout, QAIssue, QAReport
from pdfbook.layout.flow import split_translation
from pdfbook.layout.hyphenation import Hyphenation
from pdfbook.qa.checks_geometry import run_box
from pdfbook.qa.checks_glossary import check_glossary
from pdfbook.qa.checks_glyphs import check_page_glyphs
from pdfbook.qa.checks_visual import check_page_visual
from pdfbook.qa.report import gate, write_report
from pdfbook.rendering.vector_renderer import PageRenderResult, VectorRenderer
from pdfbook.translation.pipeline import TranslationOutcome, TranslationPipeline

from .page_plan import PagePlan, block_units, build_plans
from .runtime import Runtime

__all__ = ["JobResult", "JobSpec", "TranslationJob", "block_units", "build_plans"]

log = logging.getLogger(__name__)

_CONTEXT_CHARS = 1500


@dataclass(frozen=True)
class JobSpec:
    """Cosa tradurre, dove salvarlo e con quali impostazioni."""

    input_pdf: Path
    output_pdf: Path
    settings: AppSettings
    page_start: int | None = None
    page_end: int | None = None
    missing_policy: str = "skip"
    overflow_policy: str = "keep_size"


@dataclass
class JobResult:
    """Esito del job: file prodotti, report e conteggi."""

    output_pdf: Path
    report_path: Path
    report: QAReport
    pages: int = 0
    blocks: int = 0
    summary: dict[str, int] = field(default_factory=dict)

    def violations(self) -> list[str]:
        """Violazioni del gate di pubblicazione (vuoto = accettabile)."""
        return gate(self.report)


class TranslationJob:
    """Esegue la traduzione di un documento su un ``Runtime``."""

    def __init__(self, spec: JobSpec, runtime: Runtime, *, sleep=time.sleep) -> None:
        self.spec = spec
        self.runtime = runtime
        self.sleep = sleep

    # ---------- API ----------

    def run(self, progress=None) -> JobResult:
        """Traduce le pagine richieste, salva il PDF e il report QA."""
        first, last = self._range()
        pages = [self.runtime.source.page(index) for index in range(first, last + 1)]
        plans = build_plans(pages, stitch=self.spec.settings.stitch_paragraphs)
        translator = self._translator()
        renderer = self._renderer(translator)
        report = QAReport()
        counters = {"blocks": 0, "perfect": 0, "overflow_shifted": 0, "stitched": 0}
        previous: str | None = None
        total = last - first + 1
        try:
            for done, plan in enumerate(plans, start=1):
                page = plan.page
                translations = self._translate_plan(plans, done - 1, translator, previous, report, counters)
                canvas = self.runtime.canvas_factory(first + done - 1)
                before = self._snapshot(canvas)
                rendered = renderer.render_page(canvas, page, translations)
                self._merge(report, rendered, counters)
                if before is not None:
                    self._check_visual(report, page, before, rendered, canvas)
                for issue in check_page_glyphs(
                    page.number, list(translations.values()), canvas.text()
                ):
                    report.add(issue)
                previous = self._page_text(page)
                if progress:
                    progress(done, total, f"pagina {page.number}: {counters['blocks']} blocchi")
            if counters["blocks"] == 0:
                raise ValueError(
                    "Il PDF non contiene testo selezionabile: serve un PDF con testo nativo."
                )
            output = self._save()
            counters.update(self.runtime.stats())
            report_path = write_report(output, report, counters=counters)
        finally:
            self.runtime.close()
        result = JobResult(
            output_pdf=Path(output),
            report_path=report_path,
            report=report,
            pages=total,
            blocks=counters["blocks"],
            summary=dict(counters),
        )
        log.info(
            "job completato: %s pagine, %s blocchi, %s issue",
            result.pages, result.blocks, len(report.issues),
        )
        return result

    # ---------- passi ----------

    def _range(self) -> tuple[int, int]:
        total = self.runtime.source.page_count
        first = max(0, (self.spec.page_start or 1) - 1)
        last = min(total - 1, (self.spec.page_end or total) - 1)
        if last < first:
            raise ValueError("intervallo di pagine non valido")
        return first, last

    def _translator(self) -> TranslationPipeline:
        settings = self.spec.settings.translation_settings()
        return TranslationPipeline(
            provider=self.runtime.provider,
            cache=self.runtime.cache,
            settings=settings,
            sleep=self.sleep,
        )

    def _renderer(self, translator: TranslationPipeline) -> VectorRenderer:
        language = self.spec.settings.target_lang
        return VectorRenderer(
            self.runtime.resolver,
            hyphenation=Hyphenation(language),
            shortener=translator,
            missing_policy=self.spec.missing_policy,
            overflow_policy=self.spec.overflow_policy,
        )

    def _translate_plan(
        self,
        plans: list[PagePlan],
        index: int,
        translator: TranslationPipeline,
        previous: str | None,
        report: QAReport,
        counters: dict[str, int],
    ) -> dict[str, str]:
        """Traduce le unità che iniziano su questa pagina e ricolloca le continuazioni."""
        plan = plans[index]
        translations = dict(plan.incoming)
        if not plan.requests:
            return translations
        outcome: TranslationOutcome = translator.translate(plan.requests, context=previous)
        for issue in check_glossary(
            plan.page.number,
            plan.requests,
            outcome.translations,
            self.spec.settings.glossary,
        ):
            report.add(issue)
        for unit_key, value in outcome.translations.items():
            target = plan.targets.get(unit_key)
            if target is None:
                continue
            if target.second_block is None:
                translations[target.first_block] = value
                continue
            self._apply_split(plan, plans, index, target, value, translations, report, counters)
        return translations

    @staticmethod
    def _apply_split(
        plan: PagePlan,
        plans: list[PagePlan],
        index: int,
        target,
        translated: str,
        translations: dict[str, str],
        report: QAReport,
        counters: dict[str, int],
    ) -> None:
        split = split_translation(target.first_text, target.second_text, translated)
        translations[target.first_block] = split.first
        if not split.usable:
            report.add(
                QAIssue(
                    page=plan.page.number,
                    kind=IssueKind.SPLIT_FAILED,
                    block=target.first_block,
                    detail=f"non divisibile: {target.second_block} resta senza traduzione",
                )
            )
            return
        plans[index + 1].incoming[target.second_block] = split.second
        counters["stitched"] += 1
        report.add(
            QAIssue(
                page=plan.page.number,
                kind=IssueKind.PARAGRAPH_STITCHED,
                block=target.first_block,
                detail=f"continua in {target.second_block} (pagina {plans[index + 1].page.number})",
            )
        )

    @staticmethod
    def _merge(report: QAReport, rendered: PageRenderResult, counters: dict[str, int]) -> None:
        for issue in rendered.issues:
            report.add(issue)
        counters["blocks"] += rendered.blocks
        counters["perfect"] += rendered.perfect
        counters["overflow_shifted"] += rendered.shifted

    @staticmethod
    def _page_text(page: PageLayout) -> str:
        return "\n".join(block.text for block in page.text_blocks())[:_CONTEXT_CHARS]

    def _snapshot(self, canvas) -> object | None:
        """Immagine della pagina **prima** della redazione, se il QA visivo è attivo."""
        if not self.spec.settings.visual_qa:
            return None
        return canvas.snapshot(self.spec.settings.visual_qa_dpi)

    def _check_visual(self, report: QAReport, page: PageLayout, before, rendered, canvas) -> None:
        after = canvas.snapshot(self.spec.settings.visual_qa_dpi)
        masked = [block.bbox for block in page.blocks]
        masked.extend(run_box(run) for run in rendered.runs)
        for issue in check_page_visual(
            page.number, before, after, text_boxes=masked
        ):
            report.add(issue)

    def _save(self) -> str:
        self.runtime.cache.save()
        target = str(self.spec.output_pdf)
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        self.runtime.save(target)
        return target
