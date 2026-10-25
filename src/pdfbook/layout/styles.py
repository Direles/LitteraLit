"""Stili inline: grassetto e corsivo conservati con marcatori (Fase 1.1/1.2).

Il problema: un blocco è reso con il font del **primo** span, quindi grassetti e corsivi
spariscono. La soluzione è un **round-trip con marcatori**:

1. il testo da tradurre porta i tag ``<b>…</b>`` e ``<i>…</i>`` attorno alle parti enfatizzate;
2. il prompt chiede di conservarli (il modello li tratta come parte del testo);
3. al ritorno i tag diventano segmenti tipografici, disegnati con il font giusto.

Se i tag tornano assenti o sbilanciati non si inventa nulla: si disegna tutto nel font
dominante e si registra ``style_flattened`` (informativa).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pdfbook.domain.models import TextBlock

from ..fonts.platform_fonts import classify

__all__ = [
    "BOLD_CLOSE",
    "BOLD_OPEN",
    "ITALIC_CLOSE",
    "ITALIC_OPEN",
    "StyledPiece",
    "block_has_emphasis",
    "has_markers",
    "parse_tagged",
    "plain_text",
    "strip_markup",
    "tag_block_text",
    "wrap_pieces",
]

BOLD_OPEN, BOLD_CLOSE = "<b>", "</b>"
ITALIC_OPEN, ITALIC_CLOSE = "<i>", "</i>"
_TAG = re.compile(r"</?[bi]>")
_TAG_SPLIT = re.compile(r"(</?[bi]>)")

Measure = Callable[[str, bool, bool, float], float]


@dataclass(frozen=True)
class StyledPiece:
    """Una parola con il suo stile."""

    text: str
    bold: bool = False
    italic: bool = False


def block_has_emphasis(block: TextBlock) -> bool:
    """``True`` se almeno uno span del blocco è grassetto o corsivo."""
    for line in block.lines:
        for span in line.spans:
            _, bold, italic = classify(span.font_name)
            if bold or italic:
                return True
    return False


def tag_block_text(block: TextBlock) -> str:
    """Testo del blocco con i tag attorno agli span enfatizzati, riga per riga."""
    lines: list[str] = []
    for line in block.lines:
        chunks: list[str] = []
        for span in line.spans:
            if not span.text:
                continue
            _, bold, italic = classify(span.font_name)
            text = span.text
            if bold:
                text = f"{BOLD_OPEN}{text}{BOLD_CLOSE}"
            if italic:
                text = f"{ITALIC_OPEN}{text}{ITALIC_CLOSE}"
            chunks.append(text)
        lines.append("".join(chunks))
    return "\n".join(lines).strip()


def has_markers(text: str) -> bool:
    return BOLD_OPEN in text or ITALIC_OPEN in text


def strip_markup(text: str) -> str:
    """Rimuove i marcatori di stile (serve ai controlli di testo)."""
    return _TAG.sub("", text)


def parse_tagged(text: str) -> list[StyledPiece]:
    """Da testo con tag a parole con stile, nell'ordine di apparizione."""
    words = _TAG.sub(" ", text).split()
    states = _word_states(text)
    return [
        StyledPiece(word, *states[index]) if index < len(states) else StyledPiece(word)
        for index, word in enumerate(words)
    ]


def plain_text(pieces: Sequence[StyledPiece]) -> str:
    return " ".join(piece.text for piece in pieces)


def wrap_pieces(
    pieces: Sequence[StyledPiece],
    *,
    measure: Measure,
    size: float,
    max_width: float,
) -> list[list[StyledPiece]]:
    """A capo goloso con le metriche del font di ogni parola (niente sillabazione)."""
    lines: list[list[StyledPiece]] = []
    current: list[StyledPiece] = []
    width = 0.0
    space = measure(" ", False, False, size)
    for piece in pieces:
        piece_width = measure(piece.text, piece.bold, piece.italic, size)
        extra = piece_width + (space if current else 0.0)
        if current and width + extra > max_width:
            lines.append(current)
            current, width = [piece], piece_width
            continue
        current.append(piece)
        width += extra
    if current:
        lines.append(current)
    return lines


def _word_states(text: str) -> list[tuple[bool, bool]]:
    """Stato ``(bold, italic)`` per ogni parola, seguendo i tag in ordine."""
    states: list[tuple[bool, bool]] = []
    bold = italic = False
    for part in _TAG_SPLIT.split(text):
        if part == BOLD_OPEN:
            bold = True
        elif part == BOLD_CLOSE:
            bold = False
        elif part == ITALIC_OPEN:
            italic = True
        elif part == ITALIC_CLOSE:
            italic = False
        else:
            states.extend([(bold, italic)] * len(part.split()))
    return states
