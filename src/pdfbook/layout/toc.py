"""Riconoscimento e ricomposizione delle righe d'indice (M6/M7).

Una riga d'indice è ``Titolo + riempimento + numero di pagina``: se la traduzione
allunga il titolo, i puntini originali non allineano più il numero. Qui si riconosce
la struttura e si **ricalcola** il riempimento sulla larghezza disponibile.

La misura è iniettata (``measure(text) -> larghezza``), così il modulo è testabile
senza font e riutilizzabile con qualsiasi motore tipografico.
"""

from __future__ import annotations

import re
from collections.abc import Callable

__all__ = ["TOC_LINE_RE", "is_toc_line", "optimize_toc_line"]

TOC_LINE_RE = re.compile(r"^(.*?)([\.\s_\-]{4,})\s*((?:[ivxlcdmIVXLCDM]+|\d+))\s*$")
_FILL_CANDIDATES = (". ", ".", "_", "-", " ")


def is_toc_line(text: str) -> bool:
    """``True`` se la riga ha la forma tipica di una voce d'indice."""
    return bool(TOC_LINE_RE.match(text.strip()))


def optimize_toc_line(
    text: str,
    *,
    measure: Callable[[str], float],
    max_width: float,
) -> str:
    """Riallinea i puntini di riempimento entro ``max_width`` (testo invariato se non è TOC)."""
    match = TOC_LINE_RE.match(text.strip())
    if not match:
        return text
    title = match.group(1).strip()
    original_fill = match.group(2)
    page = match.group(3).strip()
    if not title:
        return text

    width_title = measure(title)
    width_page = measure("  " + page)
    width_fill = max_width - width_title - width_page
    if width_fill <= 0:
        return text

    for fill in _FILL_CANDIDATES:
        char = fill.strip()
        if char and char in original_fill:
            return title + _repeat(fill, width_fill, measure) + "  " + page
    return title + _repeat(" ", width_fill, measure) + "  " + page


def _repeat(fill: str, width: float, measure: Callable[[str], float]) -> str:
    """Ripete ``fill`` quante volte serve per coprire ``width`` senza superarla."""
    unit = measure(fill)
    if unit <= 0:
        return ""
    count = int(width / unit)
    while count > 0 and measure(fill * count) > width:
        count -= 1
    return fill * max(0, count)
