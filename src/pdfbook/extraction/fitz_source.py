"""Adattatore PyMuPDF per l'estrazione (M8).

Unico punto in cui l'estrazione tocca ``fitz``: apre il documento e fornisce, pagina per
pagina, il dizionario grezzo più le misure della pagina richieste da ``pdf_extractor``.
"""

from __future__ import annotations

from typing import Any

import pymupdf as fitz

from pdfbook.domain.models import PageLayout

from .pdf_extractor import extract_page

__all__ = ["PdfPageSource"]


class PdfPageSource:
    """Sorgente di ``PageLayout`` da un PDF con testo nativo."""

    def __init__(self, doc: Any) -> None:
        self.doc = doc

    @classmethod
    def open(cls, pdf_path: str) -> PdfPageSource:
        return cls(fitz.open(pdf_path))

    @property
    def page_count(self) -> int:
        return len(self.doc)

    def page(self, index: int) -> PageLayout:
        page = self.doc[index]
        return extract_page(
            page.get_text("dict"),
            number=index + 1,
            width=page.rect.width,
            height=page.rect.height,
        )

    def close(self) -> None:
        self.doc.close()
