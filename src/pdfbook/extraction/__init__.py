"""Estrazione: da PDF a ``PageLayout``.

Il modulo non importa PyMuPDF: lavora sul dizionario prodotto da
``page.get_text('dict')`` e su due misure (larghezza/altezza pagina). Questo lo rende
testabile con fixture JSON e riutilizzabile con qualunque sorgente compatibile.
"""

from .fitz_source import PdfPageSource
from .pdf_extractor import block_from_raw, extract_page, line_from_raw, span_from_raw

__all__ = ["PdfPageSource", "block_from_raw", "extract_page", "line_from_raw", "span_from_raw"]
