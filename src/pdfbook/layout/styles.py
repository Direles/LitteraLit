"""Stili inline: grassetto, corsivo, apici e pedici conservati con marcatori (Fase 1).

Il problema: un blocco è reso con il font del **primo** span, quindi grassetti, corsivi e
riferimenti di nota spariscono. La soluzione è un **round-trip con marcatori**:

1. il testo da tradurre porta i tag ``<b>…</b>``, ``<i>…</i>``, ``<sup>…</sup>``,
   ``<sub>…</sub>`` attorno alle parti enfatizzate;
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
from .scripts import block_has_script, script_of, script_scale

__all__ = [
    "BOLD_CLOSE",
    "BOLD_OPEN",
    "ITALIC_CLOSE",
    "ITALIC_OPEN",
    "SUB_CLOSE",
    "SUB_OPEN",
    "SUBSCRIPT",
    "SUP_CLOSE",
    "SUP_OPEN",
    "SUPERSCRIPT",
    "StyledPiece",
    "block_has_emphasis",
    "block_needs_tags",
    "has_markers",
    "parse_tagged",
    "piece_size",
    "plain_text",
    "strip_markup",
    "tag_block_text",
    "wrap_pieces",
]

BOLD_OPEN, BOLD_CLOSE = "<b>", "</b>"
ITALIC_OPEN, ITALIC_CLOSE = "<i>", "</i>"
SUP_OPEN, SUP_CLOSE = "<sup>", "</sup>"
SUB_OPEN, SUB_CLOSE = "<sub>", "</sub>"

SUPERSCRIPT, SUBSCRIPT = "sup", "sub"

_TAG = re.compile(r"</?(?:b|i|sup|sub)>")
_TAG_SPLIT = re.compile(r"(</?(?:b|i|sup|sub)>)")

_OPENS = {
    BOLD_OPEN: ("bold", True),
    ITALIC_OPEN: ("italic", True),
    SUP_OPEN: ("script", SUPERSCRIPT),
    SUB_OPEN: ("script", SUBSCRIPT),
}
_CLOSES = {
    BOLD_CLOSE: ("bold", None),
    ITALIC_CLOSE: ("italic", None),
    SUP_CLOSE: ("script", None),
    SUB_CLOSE: ("script", None),
}

Measure = Callable[["StyledPiece", float], float]


@dataclass(frozen=True)
class StyledPiece:
    """Una parola con il suo stile; ``script`` vale ``"sup"``, ``"sub"`` o ``None``."""

    text: str
    bold: bool = False
    italic: bool = False
    script: str | None = None


def block_has_emphasis(block: TextBlock) -> bool:
    """``True`` se almeno uno span del blocco è grassetto o corsivo."""
    for line in block.lines:
        for span in line.spans:
            _, bold, italic = classify(span.font_name)
            if bold or italic:
                return True
    return False


def block_needs_tags(block: TextBlock) -> bool:
    """``True`` se il blocco va tradotto con i marcatori (stili o apici/pedici)."""
    return block_has_emphasis(block) or block_has_script(block)


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
            script = script_of(span, line)
            if script == SUPERSCRIPT:
                text = f"{SUP_OPEN}{text}{SUP_CLOSE}"
            elif script == SUBSCRIPT:
                text = f"{SUB_OPEN}{text}{SUB_CLOSE}"
            chunks.append(text)
        lines.append("".join(chunks))
    return "\n".join(lines).strip()


def has_markers(text: str) -> bool:
    return any(tag in text for tag in (BOLD_OPEN, ITALIC_OPEN, SUP_OPEN, SUB_OPEN))


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


def piece_size(piece: StyledPiece, size: float) -> float:
    """Corpo effettivo della parola: apici e pedici sono più piccoli."""
    return size * script_scale(piece.script)


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
    space = measure(StyledPiece(" "), size)
    for piece in pieces:
        piece_width = measure(piece, size)
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


def _word_states(text: str) -> list[tuple[bool, bool, str | None]]:
    """Stato ``(bold, italic, script)`` per ogni parola, seguendo i tag in ordine."""
    states: list[tuple[bool, bool, str | None]] = []
    bold = italic = False
    script: str | None = None
    for part in _TAG_SPLIT.split(text):
        if part in _OPENS:
            field, value = _OPENS[part]
            if field == "bold":
                bold = True
            elif field == "italic":
                italic = True
            else:
                script = value
        elif part in _CLOSES:
            field, _ = _CLOSES[part]
            if field == "bold":
                bold = False
            elif field == "italic":
                italic = False
            else:
                script = None
        else:
            states.extend([(bold, italic, script)] * len(part.split()))
    return states
