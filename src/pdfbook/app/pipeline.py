"""Pipeline di documento (M11): PDF → pagine → traduzione → rendering → QA.

Il job è l'unico punto che conosce il *flusso*: legge le pagine, costruisce il batch di
traduzione, delega rendering e QA, salva e chiude. Non contiene né HTTP né disegno.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from pdfbook.config.settings import AppSettings
from pdfbook.domain.models import PageLayout, QAReport
from pdfbook.layout.hyphenation import Hyphenation
from pdfbook.layout.segmentation import is_structured_block
from pdfbook.qa.checks_geometry import run_box
from pdfbook.qa.checks_glyphs import check_page_glyphs
from pdfbook.qa.checks_visual import check_page_visual
from pdfbook.qa.report import gate, write_report
from pdfbook.rendering.vector_renderer import PageRenderResult, VectorRenderer
from pdfbook.translation.pipeline import TranslationOutcome, TranslationPipeline

from .runtime import Runtime

__all__ = ["JobResult", "JobSpec", "TranslationJob", "batch_for_page"]

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


def batch_for_page(page: PageLayout) -> dict[str, str]:
    """Chiavi di traduzione della pagina: ``b{i}`` per la prosa, ``b{i}_l{j}`` per le colonne."""
    batch: dict[str, str] = {}
    for block in page.blocks:
        text = block.text
        if not text.strip():
            continue
        if is_structured_block(block):
            for index, line in enumerate(block.lines):
                if line.text.strip():
                    batch[f"{block.id}_l{index}"] = line.text
        else:
            batch[block.id] = text
    return batch


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
        translator = self._translator()
        renderer = self._renderer(translator)
        report = QAReport()
        counters = {"blocks": 0, "perfect": 0, "overflow_shifted": 0}
        previous: str | None = None
        total = last - first + 1
        try:
            for done, index in enumerate(range(first, last + 1), start=1):
                page = self.runtime.source.page(index)
                translations = self._translate(translator, page, previous)
                canvas = self.runtime.canvas_factory(index)
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
                    progress(done, total, f"pagina {index + 1}: {counters['blocks']} blocchi")
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

    @staticmethod
    def _translate(
        translator: TranslationPipeline, page: PageLayout, previous: str | None
    ) -> Mapping[str, str]:
        batch = batch_for_page(page)
        if not batch:
            return {}
        outcome: TranslationOutcome = translator.translate(batch, context=previous)
        return outcome.translations

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
