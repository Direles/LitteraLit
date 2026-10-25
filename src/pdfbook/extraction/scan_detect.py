"""Riconoscimento di pagine scansionate (Fase 4.1).

Un PDF "fotocopiato" non ha uno strato di testo: la pipeline non può tradurre nulla e
l'utente riceve un errore. Qui si distingue il caso *scansione* dal caso *estrazione
fallita*, così il messaggio può dire cosa fare (``ocrmypdf``) invece di cosa è andato storto.

Il modulo non fa OCR: classifica soltanto. L'adapter OCR arriverà in Fase 4.2 e userà questa
classificazione per decidere se intervenire.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pdfbook.domain.models import PageLayout

__all__ = [
    "MIN_TEXT_CHARS",
    "ScanReport",
    "has_text",
    "is_scanned_page",
    "scan_report",
]

#: Sotto questa soglia di caratteri (senza spazi) una pagina è "senza testo utile".
MIN_TEXT_CHARS = 20


def has_text(page: PageLayout) -> bool:
    """``True`` se la pagina ha abbastanza caratteri da poter essere tradotta."""
    chars = sum(len(block.text.strip()) for block in page.blocks)
    return chars >= MIN_TEXT_CHARS


def is_scanned_page(page: PageLayout) -> bool:
    """Pagina senza testo utile ma con immagini: è quasi certamente una scansione."""
    return not has_text(page) and bool(page.image_boxes)


@dataclass(frozen=True)
class ScanReport:
    """Fotografia del documento: quante pagine hanno testo e quante sembrano scansioni."""

    pages: int
    with_text: int
    scanned: tuple[int, ...]

    @property
    def all_scanned(self) -> bool:
        return self.pages > 0 and self.with_text == 0 and len(self.scanned) == self.pages

    @property
    def mostly_scanned(self) -> bool:
        return len(self.scanned) * 2 > self.pages

    def message(self) -> str:
        """Messaggio azionabile per l'utente (italiano, nessun gergo interno)."""
        if self.all_scanned:
            return (
                f"Il PDF sembra una scansione: {self.pages} pagine senza testo, solo immagini.\n"
                "Serve un OCR prima della traduzione: `ocrmypdf --language ita+eng in.pdf out.pdf` "
                "(oppure usare un PDF con testo selezionabile)."
            )
        if self.mostly_scanned:
            pages = ", ".join(str(number) for number in self.scanned[:12])
            extra = "…" if len(self.scanned) > 12 else ""
            return (
                f"{len(self.scanned)} pagine su {self.pages} sembrano scansioni (pagine {pages}{extra}).\n"
                "Le pagine senza testo verranno saltate; per tradurle serve un OCR preliminare."
            )
        if self.scanned:
            pages = ", ".join(str(number) for number in self.scanned[:12])
            extra = "…" if len(self.scanned) > 12 else ""
            return (
                f"Pagine senza testo, probabilmente scansioni (pagine {pages}{extra}).\n"
                "Verranno saltate; per tradurle serve un OCR preliminare (`ocrmypdf`)."
            )
        return (
            "Il PDF non contiene testo selezionabile: serve un PDF con testo nativo "
            "oppure un OCR preliminare (`ocrmypdf`)."
        )


def scan_report(pages: Sequence[PageLayout]) -> ScanReport:
    """Analizza le pagine estratte e restituisce il conteggio delle scansioni."""
    scanned = tuple(page.number for page in pages if is_scanned_page(page))
    with_text = sum(1 for page in pages if has_text(page))
    return ScanReport(pages=len(pages), with_text=with_text, scanned=scanned)
