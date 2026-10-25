"""Rendering di pagina con il QA annesso (Fase 0/3).

Sequenza unica e riusabile: fotografia → rendering → contatori → controllo visivo →
controllo glifi. Tenerla fuori dal job evita che l'orchestrazione conosca i dettagli del QA.
"""

from __future__ import annotations

from pdfbook.config.settings import AppSettings
from pdfbook.domain.models import IssueKind, PageLayout, QAIssue, QAReport
from pdfbook.extraction.scan_detect import is_scanned_page
from pdfbook.layout.styles import strip_markup
from pdfbook.layout.writing_system import text_blocks_outside
from pdfbook.qa.checks_glyphs import check_page_glyphs
from pdfbook.qa.checks_roundtrip import check_roundtrip
from pdfbook.rendering.vector_renderer import VectorRenderer

from .visual_qa import check_after_render, snapshot

__all__ = ["render_and_check"]


def render_and_check(
    *,
    canvas,
    page: PageLayout,
    renderer: VectorRenderer,
    translations: dict[str, str],
    report: QAReport,
    counters: dict[str, int],
    settings: AppSettings,
) -> None:
    """Disegna la pagina e registra issue e contatori."""
    before = snapshot(canvas, enabled=settings.visual_qa, dpi=settings.visual_qa_dpi)
    rendered = renderer.render_page(canvas, page, translations)

    for issue in rendered.issues:
        report.add(issue)
    if is_scanned_page(page):
        report.add(
            QAIssue(
                page=page.number,
                kind=IssueKind.SCAN_PAGE,
                detail="pagina senza testo (probabile scansione): serve un OCR preliminare",
            )
        )
    for block_id, system in text_blocks_outside(page):
        report.add(
            QAIssue(
                page=page.number,
                kind=IssueKind.UNSUPPORTED_SCRIPT,
                block=block_id,
                detail=f"scrittura '{system}': il shaping/RTL non è ancora supportato dal renderer",
            )
        )
    counters["blocks"] += rendered.blocks
    counters["perfect"] += rendered.perfect
    counters["overflow_shifted"] += rendered.shifted

    check_after_render(
        report, page, before, rendered, canvas, dpi=settings.visual_qa_dpi
    )
    for issue in check_page_glyphs(
        page.number, [strip_markup(value) for value in translations.values()], canvas.text()
    ):
        report.add(issue)
    for issue in check_roundtrip(
        page.number, [strip_markup(value) for value in translations.values()], canvas.text()
    ):
        report.add(issue)
