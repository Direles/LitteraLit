"""QA visivo di pagina: confronto prima/dopo la redazione (Fase 0).

Estrae dal job la sequenza "fotografa → renderizza → confronta", che è l'unica parte del QA
che ha bisogno del canvas. Il resto delle verifiche vive in ``qa/``.
"""

from __future__ import annotations

from pdfbook.domain.models import PageLayout, QAReport
from pdfbook.qa.checks_geometry import run_box
from pdfbook.qa.checks_visual import PageImage, check_page_visual

__all__ = ["check_after_render", "snapshot"]


def snapshot(canvas, *, enabled: bool, dpi: float) -> PageImage | None:
    """Immagine della pagina **prima** della redazione, se il QA visivo è attivo."""
    if not enabled:
        return None
    return canvas.snapshot(dpi)


def check_after_render(
    report: QAReport,
    page: PageLayout,
    before: PageImage | None,
    rendered,
    canvas,
    *,
    dpi: float,
) -> None:
    """Confronta la pagina e registra le issue visive (grafica alterata, testo mancante)."""
    if before is None:
        return
    after = canvas.snapshot(dpi)
    masked = [block.bbox for block in page.blocks]
    masked.extend(run_box(run) for run in rendered.runs)
    for issue in check_page_visual(page.number, before, after, text_boxes=masked):
        report.add(issue)
