"""Anteprima prima/dopo per pagina, senza Tk (Fase 6.1).

L'anteprima utile non è "come era / come è diventato" a livello di pixel (quello lo fa il QA
visivo): è **testo a fronte**, blocco per blocco, per controllare rapidamente che la
traduzione sia al posto giusto.

Qui vive la logica: aprire i due PDF, allineare i blocchi nell'ordine di lettura e preparare
le coppie. La finestra (`preview_window.py`) si limita a mostrarle.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from pdfbook.domain.models import PageLayout
from pdfbook.extraction.fitz_source import PdfPageSource

__all__ = ["PreviewPage", "preview_page", "preview_text"]


@dataclass(frozen=True)
class PreviewPage:
    """Una pagina dell'anteprima: numero, dimensioni e coppie original/tradotto."""

    number: int
    width: float
    height: float
    pairs: list[tuple[str, str | None]] = field(default_factory=list)

    @property
    def translated(self) -> int:
        return sum(1 for _original, translated in self.pairs if translated)

    @property
    def coverage(self) -> float:
        return self.translated / len(self.pairs) if self.pairs else 1.0


def preview_page(
    original_pdf: str,
    output_pdf: str,
    page_number: int,
    *,
    opener: Callable[[str], object] = PdfPageSource.open,
) -> PreviewPage:
    """Coppie di blocchi della pagina ``page_number`` (1-based) fra originale e tradotto."""
    original_source = opener(original_pdf)
    output_source = opener(output_pdf)
    try:
        original = _page(original_source, page_number)
        output = _page(output_source, page_number)
    finally:
        _close(original_source)
        _close(output_source)
    if original is None:
        return PreviewPage(number=page_number, width=0.0, height=0.0)
    return PreviewPage(
        number=page_number,
        width=original.width,
        height=original.height,
        pairs=_pairs(original, output),
    )


def preview_text(page: PreviewPage) -> str:
    """Testo leggibile dell'anteprima (per i test e per il copia/incolla)."""
    lines: list[str] = []
    for index, (original, translated) in enumerate(page.pairs, start=1):
        lines.append(f"[{index}] ORIGINALE: {original}")
        lines.append(f"[{index}] TRADOTTO: {translated or '—'}")
    return "\n".join(lines)


def _pairs(original: PageLayout, output: PageLayout | None) -> list[tuple[str, str | None]]:
    originals = [block.text.strip() for block in original.blocks if block.text.strip()]
    translated = (
        [block.text.strip() for block in output.blocks if block.text.strip()] if output else []
    )
    pairs: list[tuple[str, str | None]] = []
    for index, text in enumerate(originals):
        pairs.append((text, translated[index] if index < len(translated) else None))
    return pairs


def _page(source, number: int) -> PageLayout | None:
    if number < 1 or number > int(getattr(source, "page_count", 0)):
        return None
    return source.page(number - 1)


def _close(source) -> None:
    closer = getattr(source, "close", None)
    if callable(closer):
        closer()
