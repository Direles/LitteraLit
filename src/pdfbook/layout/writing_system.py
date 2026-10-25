"""Riconoscimento del sistema di scrittura (Fase 4.5, parziale).

La pipeline disegna con ``TextWriter`` e il shaping dei font: latino, cirillico e greco
funzionano, mentre arabo/ebraico (RTL) e CJK richiedono HarfBuzz configurato e font con la
copertura giusta. Invece di produrre un PDF con quadratini, il job **dice** cosa non sa
ancora fare: `unsupported_script` nel report.

Il modulo è pura classificazione su code point: nessuna dipendenza, nessun font.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from pdfbook.domain.models import PageLayout

__all__ = [
    "SUPPORTED",
    "WritingSystem",
    "classify_text",
    "describes_rtl",
    "text_blocks_outside",
]

#: Sistemi che il renderer attuale gestisce senza sorprese.
SUPPORTED = frozenset({"latin", "cyrillic", "greek"})

_RANGES: tuple[tuple[int, int, str], ...] = (
    (0x0041, 0x024F, "latin"),
    (0x0370, 0x03FF, "greek"),
    (0x0400, 0x04FF, "cyrillic"),
    (0x0590, 0x05FF, "hebrew"),
    (0x0600, 0x06FF, "arabic"),
    (0x0750, 0x077F, "arabic"),
    (0x0900, 0x097F, "devanagari"),
    (0x0E00, 0x0E7F, "thai"),
    (0x3040, 0x30FF, "kana"),
    (0x3400, 0x4DBF, "han"),
    (0x4E00, 0x9FFF, "han"),
    (0xAC00, 0xD7AF, "hangul"),
)

_RTL = frozenset({"arabic", "hebrew"})


@dataclass(frozen=True)
class WritingSystem:
    """Il sistema dominante di un testo e quanto pesa."""

    name: str
    letters: int

    @property
    def supported(self) -> bool:
        return self.name in SUPPORTED or self.name == "none"


def classify_text(text: str) -> WritingSystem:
    """Sistema di scrittura dominante nel testo (``none`` se non ci sono lettere)."""
    counts: dict[str, int] = {}
    for char in text:
        if not char.isalpha():
            continue
        system = _system_of(ord(char))
        if system is None:
            continue
        counts[system] = counts.get(system, 0) + 1
    if not counts:
        return WritingSystem("none", 0)
    name = max(counts.items(), key=lambda item: (item[1], item[0]))[0]
    return WritingSystem(name, counts[name])


def describes_rtl(system: WritingSystem) -> bool:
    return system.name in _RTL


def text_blocks_outside(
    page: PageLayout, *, supported: Iterable[str] = SUPPORTED
) -> list[tuple[str, str]]:
    """Coppie ``(id_blocco, sistema)`` dei blocchi in scritture non ancora gestite."""
    allowed = set(supported)
    found: list[tuple[str, str]] = []
    for block in page.blocks:
        system = classify_text(block.text)
        if system.letters and system.name not in allowed:
            found.append((block.id, system.name))
    return found


def _system_of(code: int) -> str | None:
    for start, end, name in _RANGES:
        if start <= code <= end:
            return name
    return None
