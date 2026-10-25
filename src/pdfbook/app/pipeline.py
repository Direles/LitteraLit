"""Pipeline di documento (M11): PDF → pagine → traduzione → rendering → QA.

Il job conosce solo il *flusso*: legge le pagine, delega traduzione, rendering e QA,
salva e chiude. Nessun HTTP, nessun disegno.
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
from pdfbook.layout.tables import mark_tables
from pdfbook.qa.checks_glossary import check_glossary
from pdfbook.qa.report import gate, write_report
from pdfbook.rendering.vector_renderer import VectorRenderer
from pdfbook.translation.pipeline import TranslationOutcome, TranslationPipeline
from pdfbook.translation.ratelimit import RateLimiter

from .checkpoints import checkpoint, fingerprint, start_journal
from .costs import account_costs
from .journal import Journal, load_journal, remove_journal
from .page_plan import PagePlan, block_units, build_plans
from .page_render import render_and_check
from .page_translator import PageTranslator
from .runtime import Runtime

__all__ = [
    "JobResult",
    "JobSpec",
    "TranslationJob",
    "block_units",
    "build_plans",
    "load_journal",
]

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
    resume: bool = False


@dataclass
class JobResult:
    """Esito del job: file prodotti, report e conteggi."""

    output_pdf: Path
    report_path: Path
    report: QAReport
    pages: int = 0
    blocks: int = 0
    resumed_pages: int = 0
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
        self._offset = first
        pages = [
            mark_tables(self.runtime.source.page(index)) for index in range(first, last + 1)
        ]
        plans = build_plans(
            pages,
            stitch=self.spec.settings.stitch_paragraphs,
            inline_styles=self.spec.settings.inline_styles,
            reading_order=self.spec.settings.reading_order,
        )
        translator = self._translator()
        renderer = self._renderer(translator)
        page_translator = PageTranslator(translator, self.spec.settings.glossary, self.spec.settings.target_lang)
        report = QAReport()
        counters = {"blocks": 0, "perfect": 0, "overflow_shifted": 0, "stitched": 0}
        journal = self._start_journal(first, last)
        resumed_pages = journal.pages_done if self.spec.resume else 0
        previous: str | None = None
        total = last - first + 1
        try:
            for done in range(1, total + 1):
                previous = self._process_page(
                    plans, done, translator, page_translator, renderer, previous,
                    report, counters, journal, progress,
                )
            output, report_path = self._finalize(report, counters)
        finally:
            self.runtime.close()
        result = JobResult(
            output_pdf=Path(output),
            report_path=report_path,
            report=report,
            pages=total,
            blocks=counters["blocks"],
            resumed_pages=resumed_pages,
            summary=dict(counters),
        )
        log.info(
            "job completato: %s pagine, %s blocchi, %s issue",
            result.pages, result.blocks, len(report.issues),
        )
        return result

    def _start_journal(self, first: int, last: int) -> Journal:
        """Apre o crea il journal, verificando la coerenza della configurazione."""
        settings = self.spec.settings.translation_settings()
        return start_journal(
            input_pdf=self.spec.input_pdf,
            output_pdf=self.spec.output_pdf,
            fingerprint_value=fingerprint(
                self.spec.input_pdf,
                settings,
                page_start=self.spec.page_start,
                page_end=self.spec.page_end,
                missing_policy=self.spec.missing_policy,
                overflow_policy=self.spec.overflow_policy,
            ),
            pages_total=last - first + 1,
            resume=self.spec.resume,
        )

    def _process_page(
        self, plans, done, translator, page_translator, renderer, previous,
        report, counters, journal, progress,
    ) -> str:
        """Traduzione, rendering, QA e checkpoint di una pagina."""
        index = done - 1
        plan = plans[index]
        translations = page_translator.translate(plans, index, previous, report, counters)
        account_costs(
            model=self.spec.settings.model,
            tokens_in=translator.tokens_in,
            tokens_out=translator.tokens_out,
            counters=counters,
            max_cost=self.spec.settings.max_cost,
        )
        canvas = self.runtime.canvas_factory(self._offset + index)
        render_and_check(
            canvas=canvas,
            page=plan.page,
            renderer=renderer,
            translations=translations,
            report=report,
            counters=counters,
            settings=self.spec.settings,
        )
        checkpoint(
            journal, done, len(plans),
            self.runtime.cache, self.spec.settings.checkpoint_every,
        )
        if progress:
            progress(done, len(plans), f"pagina {plan.page.number}: {counters['blocks']} blocchi")
        return self._page_text(plan.page)

    def _finalize(self, report: QAReport, counters: dict[str, int]) -> tuple[str, Path]:
        """Controlli finali, salvataggio del PDF e del report, pulizia del journal."""
        if counters["blocks"] == 0:
            raise ValueError("Il PDF non contiene testo selezionabile: serve un PDF con testo nativo.")
        output = self._save()
        counters.update(self.runtime.stats())
        report_path = write_report(output, report, counters=counters)
        remove_journal(output)
        return output, report_path

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
            workers=self.spec.settings.workers,
            limiter=RateLimiter.from_rate(self.spec.settings.rate_limit),
        )

    def _renderer(self, translator: TranslationPipeline) -> VectorRenderer:
        language = self.spec.settings.target_lang
        return VectorRenderer(
            self.runtime.resolver,
            hyphenation=Hyphenation(language),
            shortener=translator,
            missing_policy=self.spec.missing_policy,
            overflow_policy=self.spec.overflow_policy,
            inline_styles=self.spec.settings.inline_styles,
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
    def _page_text(page: PageLayout) -> str:
        return "\n".join(block.text for block in page.text_blocks())[:_CONTEXT_CHARS]

    def _save(self) -> str:
        self.runtime.cache.save()
        target = str(self.spec.output_pdf)
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        self.runtime.save(target)
        return target
