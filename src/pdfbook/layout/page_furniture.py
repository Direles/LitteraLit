"""Header, footer e numeri di pagina (Fase 2.4).

Questi elementi non vanno tradotti: sono etichette di servizio, spesso ripetute identiche
su ogni pagina. Tradurli produce rumore (e numeri di pagina "tradotti"), quindi si
riconoscono e si lasciano invariati.

Riconoscimento per **ricorrenza**: una riga nella fascia alta o bassa della pagina,
identica (a meno di cifre e numeri romani) su più pagine, è furniture. Un numero isolato
in fascia è furniture anche su una sola pagina.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from pdfbook.domain.models import PageLayout, TextBlock

from .segmentation import is_structured_block

__all__ = [
    "MIN_PATTERN_PAGES",
    "PATTERN_SHARE",
    "ZONE_RATIO",
    "detect_furniture",
    "in_margin",
    "is_page_number",
    "normalize",
]

ZONE_RATIO = 0.10
MIN_PATTERN_PAGES = 2
PATTERN_SHARE = 0.30
_NUMBER = re.compile(r"^\d+$")
_ROMAN = re.compile(r"^[ivxlcdm]+$", re.IGNORECASE)


def is_page_number(text: str) -> bool:
    """``True`` per un numero arabo o romano isolato."""
    stripped = text.strip()
    if not stripped:
        return False
    return bool(_NUMBER.match(stripped) or _ROMAN.match(stripped))


def normalize(text: str) -> str:
    """Testo confrontabile: minuscolo, cifre e numeri romani → ``#``."""
    tokens = re.findall(r"\w+", text.lower())
    return " ".join(
        "#" if (token.isdigit() or _ROMAN.match(token)) else token for token in tokens
    )


def in_margin(block: TextBlock, page: PageLayout) -> bool:
    """``True`` se il blocco sta nella fascia alta o bassa della pagina."""
    top_limit = page.height * ZONE_RATIO
    bottom_limit = page.height * (1 - ZONE_RATIO)
    return block.bbox.y1 <= top_limit or block.bbox.y0 >= bottom_limit


def detect_furniture(pages: Sequence[PageLayout]) -> set[tuple[int, str]]:
    """Insieme ``(indice_pagina, id_blocco)`` degli elementi di servizio."""
    counts: Counter[str] = Counter()
    candidates: list[tuple[int, str, str, bool]] = []
    for index, page in enumerate(pages):
        for block in page.blocks:
            if not block.text.strip() or is_structured_block(block):
                continue
            if not in_margin(block, page):
                continue
            key = normalize(block.text)
            counts[key] += 1
            candidates.append((index, block.id, key, is_page_number(block.text)))

    threshold = max(MIN_PATTERN_PAGES, int(len(pages) * PATTERN_SHARE))
    furniture: set[tuple[int, str]] = set()
    for index, block_id, key, numeric in candidates:
        if numeric or counts[key] >= threshold:
            furniture.add((index, block_id))
    return furniture
