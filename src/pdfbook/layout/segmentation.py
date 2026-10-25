"""Segmentazione dei blocchi: righe affiancate, indici, classificazione (M7).

Il renderer deve sapere **come** trattare un blocco prima di disegnarlo: come prosa
(fitting su tutto il blocco) o riga per riga (indice, intestazioni con colonne affiancate).
Qui vivono quelle decisioni, espresse su ``domain.models`` e senza alcuna dipendenza
dal rendering.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace

from pdfbook.domain.models import BlockKind, Line, Rect, TextBlock

from .toc import is_toc_line

__all__ = [
    "ROW_Y_TOLERANCE",
    "classify_block",
    "group_rows",
    "has_multi_column_row",
    "is_structured_block",
    "toc_ratio",
]

# Due righe con baseline entro questa tolleranza sono colonne della stessa riga visiva.
ROW_Y_TOLERANCE = 2.0
TOC_STRUCTURED_THRESHOLD = 0.5

_HEADING_RE = re.compile(
    r"^(capitolo|chapter|parte|part|appendice|appendix|indice|contents|sommario)\b",
    re.IGNORECASE,
)
_LIST_RE = re.compile(r"^\s*([■•·▪‣\-–—]|\d{1,2}[.)]|[a-z][.)])\s+")
_ROMAN_OR_NUMBER = re.compile(r"^(?:[ivxlcdm]+|\d+)$", re.IGNORECASE)


def group_rows(lines: Sequence[Line], tolerance: float = ROW_Y_TOLERANCE) -> list[list[Line]]:
    """Raggruppa le righe per baseline: ogni gruppo è una riga visiva (eventualmente a colonne)."""
    rows: list[list[Line]] = []
    for line in sorted(lines, key=lambda item: (item.origin_y, item.bbox.x0)):
        for row in rows:
            if abs(row[0].origin_y - line.origin_y) <= tolerance:
                row.append(line)
                break
        else:
            rows.append([line])
    for row in rows:
        row.sort(key=lambda item: item.bbox.x0)
    return rows


def has_multi_column_row(lines: Sequence[Line]) -> bool:
    """``True`` se almeno una riga visiva contiene più segmenti affiancati."""
    return any(len(row) > 1 for row in group_rows(lines))


def toc_ratio(lines: Sequence[Line]) -> float:
    """Frazione di righe che hanno la forma di una voce d'indice."""
    if not lines:
        return 0.0
    return sum(1 for line in lines if is_toc_line(line.text)) / len(lines)


def is_structured_block(block: TextBlock) -> bool:
    """Un blocco va trattato riga per riga se è a colonne o è un indice."""
    if block.line_count < 2:
        return False
    return has_multi_column_row(block.lines) or toc_ratio(block.lines) >= TOC_STRUCTURED_THRESHOLD


def classify_block(block: TextBlock, *, page_area: Rect | None = None) -> TextBlock:
    """Restituisce il blocco con il ``kind`` dedotto (nessuna mutazione dell'originale).

    Una classificazione **esplicita** (diversa da ``UNKNOWN``) vince sempre: chi ha già
    riconosciuto una cella di tabella o un elemento di servizio non deve vedersela
    sovrascrivere dalle euristiche.
    """
    if block.kind is not BlockKind.UNKNOWN:
        return block
    kind = _deduce_kind(block)
    if kind is block.kind:
        return block
    return replace(block, kind=kind)


def _deduce_kind(block: TextBlock) -> BlockKind:
    text = block.text.strip()
    if not text:
        return BlockKind.UNKNOWN
    if block.line_count >= 2 and toc_ratio(block.lines) >= TOC_STRUCTURED_THRESHOLD:
        return BlockKind.TOC_ROW
    if _looks_like_heading(text, block):
        return BlockKind.TITLE
    if _LIST_RE.match(text):
        return BlockKind.LIST_ITEM
    if _is_number_only(text):
        return BlockKind.CAPTION
    return BlockKind.PARAGRAPH


def _looks_like_heading(text: str, block: TextBlock) -> bool:
    first_line = block.lines[0].text.strip()
    if _HEADING_RE.match(first_line):
        return True
    if len(text) <= 80 and text.endswith(":") and len(text.split()) <= 6:
        return True
    letters = [char for char in text if char.isalpha()]
    upper_only = bool(letters) and all(char.isupper() for char in letters)
    return upper_only and len(text) <= 120


def _is_number_only(text: str) -> bool:
    """Numero di pagina o cifra romana isolata: tipicamente un numero senza didascalia."""
    return bool(_ROMAN_OR_NUMBER.match(text.strip()))
