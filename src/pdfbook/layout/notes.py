"""Note a piè di pagina (Fase 2.6).

Una nota sta in fondo alla pagina, in corpo più piccolo del testo, e inizia con un
riferimento (numero, cifra romana, asterisco…). Riconoscerla serve a due cose:

* il **riferimento a apice** nel corpo non deve essere confuso con testo che sfora;
* la nota non deve essere **cucita** alla pagina successiva: è testo autonomo, e il
  paragraph stitching la unirebbe al primo paragrafo della pagina dopo.

Il riconoscimento è prudente: corpo più piccolo del dominante **e** posizione nella fascia
bassa **e** marcatore iniziale. Se manca uno dei tre segnali il blocco resta prosa.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace

from pdfbook.domain.models import BlockKind, PageLayout, TextBlock

from .scripts import dominant_size

__all__ = [
    "BOTTOM_SHARE",
    "SMALL_SHARE",
    "footnote_ids",
    "is_footnote_block",
    "mark_notes",
    "page_body_size",
]

#: La nota deve iniziare sotto questa frazione dell'altezza della pagina.
BOTTOM_SHARE = 0.72
#: La nota è più piccola di questa frazione del corpo dominante della pagina.
SMALL_SHARE = 0.95
#: Caratteri minimi: evita di classificare come nota un numero di pagina isolato.
MIN_CHARS = 8

_MARKER = re.compile(r"^\s*(?:\d{1,3}|[ivxlcdm]{1,6}|[*†‡§¶])\s*[.)]?\s+\S", re.IGNORECASE)


def page_body_size(page: PageLayout) -> float:
    """Corpo dominante della pagina, pesato sui caratteri dei blocchi di prosa."""
    weights: dict[float, int] = {}
    for block in page.blocks:
        if block.kind in (BlockKind.TABLE_CELL, BlockKind.FOOTNOTE):
            continue
        size = dominant_size(block.lines[0]) if block.lines else 0.0
        if size <= 0:
            continue
        chars = len(block.text.strip())
        weights[round(size, 1)] = weights.get(round(size, 1), 0) + max(chars, 1)
    if not weights:
        return 0.0
    return max(weights.items(), key=lambda item: item[1])[0]


def is_footnote_block(block: TextBlock, *, body_size: float, page_height: float) -> bool:
    """``True`` se il blocco ha la forma di una nota a piè di pagina."""
    text = block.text.strip()
    if len(text) < MIN_CHARS or not block.lines:
        return False
    if body_size <= 0 or page_height <= 0:
        return False
    if block.bbox.y0 < page_height * BOTTOM_SHARE:
        return False
    size = dominant_size(block.lines[0])
    if size <= 0 or size > body_size * SMALL_SHARE:
        return False
    return bool(_MARKER.match(text))


def mark_notes(page: PageLayout) -> PageLayout:
    """Restituisce la pagina con i blocchi di nota marcati ``FOOTNOTE``."""
    body = page_body_size(page)
    marked = [
        block
        if block.kind is not BlockKind.UNKNOWN
        or not is_footnote_block(block, body_size=body, page_height=page.height)
        else replace(block, kind=BlockKind.FOOTNOTE)
        for block in page.blocks
    ]
    if all(new is old for new, old in zip(marked, page.blocks, strict=True)):
        return page
    return replace(page, blocks=marked)


def footnote_ids(blocks: Sequence[TextBlock]) -> set[str]:
    return {block.id for block in blocks if block.kind is BlockKind.FOOTNOTE}
