"""Adattatore PyMuPDF per `fonts` (M5).

Tiene l'unica dipendenza da ``fitz`` fuori dal resolver: qui si converte un documento
in ``EmbeddedFontSource`` e si creano oggetti ``fitz.Font`` da buffer, file o base-14.
Non contiene logica di scelta: quella è in ``resolver.py``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pymupdf as fitz

__all__ = ["PdfFontSource", "make_fitz_font"]


class PdfFontSource:
    """Espone i font di un ``fitz.Document`` secondo il protocollo ``EmbeddedFontSource``."""

    def __init__(self, doc: Any) -> None:
        self.doc = doc

    @classmethod
    def open(cls, pdf_path: str) -> PdfFontSource:
        return cls(fitz.open(pdf_path))

    @property
    def page_count(self) -> int:
        return len(self.doc)

    def page_fonts(self, page_index: int) -> Sequence[tuple[int, str]]:
        try:
            fonts = self.doc.get_page_fonts(page_index, full=True)
        except Exception:  # noqa: BLE001 - pagina senza font: nessun font da estrarre
            return ()
        return [(int(entry[0]), str(entry[3])) for entry in fonts if int(entry[0]) > 0]

    def extract_font(self, xref: int) -> tuple[str, str, str, bytes | None]:
        name, ext, kind, buffer = self.doc.extract_font(xref)
        return str(name), str(ext), str(kind), buffer

    def close(self) -> None:
        self.doc.close()


def make_fitz_font(
    *,
    buffer: bytes | None = None,
    path: str | None = None,
    name: str | None = None,
) -> fitz.Font:
    """Factory compatibile con ``FontResolver(font_factory=make_fitz_font)``."""
    if buffer is not None:
        return fitz.Font(fontbuffer=buffer)
    if path:
        return fitz.Font(fontfile=path)
    return fitz.Font(name or "helv")
