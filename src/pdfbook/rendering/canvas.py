"""Contratto del canvas di pagina (M9).

Il renderer non conosce PyMuPDF: chiede a un ``PageCanvas`` di rimuovere il testo
originale e di disegnare una lista di ``TextRun``. L'adattatore reale è
``rendering/fitz_canvas.py``; nei test si usa un canvas finto che registra le chiamate.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from pdfbook.domain.models import Rect
from pdfbook.qa.checks_visual import PageImage

RGB = tuple[float, float, float]

__all__ = ["PageCanvas", "TextRun"]


@dataclass(frozen=True)
class TextRun:
    """Una riga da disegnare: posizione del *baseline*, font già risolto, colore."""

    x: float
    baseline_y: float
    text: str
    font: Any
    size: float
    color: RGB
    width: float = 0.0
    block_id: str = ""


@runtime_checkable
class PageCanvas(Protocol):
    """Superficie di disegno di una pagina."""

    width: float
    height: float

    def redact(self, box: Rect) -> None: ...

    def apply_redactions(self) -> None: ...

    def draw(self, runs: Sequence[TextRun]) -> Sequence[TextRun]:
        """Disegna le righe e restituisce quelle **non** disegnate (per il QA)."""
        ...

    def text(self) -> str:
        """Testo effettivamente presente nella pagina (per il controllo dei glifi)."""
        ...

    def snapshot(self, dpi: float = 72.0) -> PageImage:
        """Immagine in scala di grigi della pagina, per il confronto visivo."""
        ...
