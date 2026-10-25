"""Parser del formato ``<|det|>`` dei VLM di OCR (Fase 4.3).

I modelli tipo Unlimited-OCR restituiscono un testo con marcatori di rilevamento:

```
<|det|>title [12, 40, 300, 62]Capitolo 1
<|det|>text [12, 80, 300, 240]Il testo del paragrafo...
```

Coordinate in pixel (assolute) o normalizzate 0–1: si distingue dal valore massimo. Il parser
non chiama la rete e non conosce il modello: trasforma una stringa in blocchi tipografici,
così il comportamento è testabile e i difetti di formato sono visibili subito.

Un blocco malformato **non** fa fallire la pagina: viene saltato e conteggiato, perché perdere
una didascalia è meglio che perdere il libro.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from pdfbook.domain.models import BlockKind, Line, PageLayout, Rect, Span, TextBlock

__all__ = ["DetBlock", "DetParseResult", "parse_det", "to_page_layout"]

_MARKER = re.compile(r"<\|det\|>\s*")
_HEAD = re.compile(r"^(?P<kind>[a-zA-Z_]+)\s*\[(?P<bbox>[^\]]*)\]\s*(?P<text>.*)$", re.DOTALL)

#: Tipo dichiarato dal modello → tipo di blocco del dominio.
_KIND_MAP: dict[str, BlockKind] = {
    "title": BlockKind.TITLE,
    "heading": BlockKind.TITLE,
    "section": BlockKind.TITLE,
    "caption": BlockKind.CAPTION,
    "figure": BlockKind.CAPTION,
    "table": BlockKind.TABLE_CELL,
    "list": BlockKind.LIST_ITEM,
    "text": BlockKind.PARAGRAPH,
    "paragraph": BlockKind.PARAGRAPH,
    "footnote": BlockKind.FOOTNOTE,
    "page_number": BlockKind.FURNITURE,
    "header": BlockKind.FURNITURE,
    "footer": BlockKind.FURNITURE,
}


@dataclass(frozen=True)
class DetBlock:
    """Un riquadro riconosciuto dal modello: tipo, coordinate e testo."""

    kind: str
    bbox: tuple[float, float, float, float]
    text: str

    def normalized(self, width: float, height: float) -> tuple[float, float, float, float]:
        """Coordinate in punti pagina, con rilevamento delle coordinate normalizzate."""
        x0, y0, x1, y1 = self.bbox
        if max(x1, y1) <= 1.5:
            return (x0 * width, y0 * height, x1 * width, y1 * height)
        return self.bbox


@dataclass
class DetParseResult:
    """Blocchi validi, righe scartate e motivo dell'ultimo scarto."""

    blocks: list[DetBlock] = field(default_factory=list)
    skipped: int = 0
    problems: list[str] = field(default_factory=list)


def parse_det(text: str) -> DetParseResult:
    """Divide l'output del modello in blocchi; scarta quelli senza coordinate valide."""
    result = DetParseResult()
    if not text or "<|det|>" not in text:
        return result
    for chunk in _MARKER.split(text):
        chunk = chunk.strip()
        if not chunk:
            continue
        match = _HEAD.match(chunk)
        if match is None:
            result.skipped += 1
            result.problems.append(f"intestazione non valida: {chunk[:40]!r}")
            continue
        coords = _coords(match.group("bbox"))
        if coords is None:
            result.skipped += 1
            result.problems.append(f"bbox non valida: {match.group('bbox')!r}")
            continue
        body = match.group("text").strip()
        if not body:
            result.skipped += 1
            continue
        result.blocks.append(DetBlock(match.group("kind").lower(), coords, body))
    return result


def to_page_layout(
    blocks: Sequence[DetBlock],
    *,
    number: int,
    width: float,
    height: float,
    size: float = 10.0,
) -> PageLayout:
    """Converte i blocchi OCR in ``PageLayout`` (una riga per blocco, stile ignoto)."""
    text_blocks: list[TextBlock] = []
    for index, block in enumerate(blocks):
        x0, y0, x1, y1 = block.normalized(width, height)
        rect = Rect(max(0.0, x0), max(0.0, y0), min(width, x1), min(height, y1))
        if rect.x1 - rect.x0 < 2 or rect.y1 - rect.y0 < 2:
            continue
        line = Line(
            spans=[Span(text=block.text, font_name="", size=size)],
            bbox=rect,
            origin_y=rect.y0 + size * 0.8,
        )
        text_blocks.append(
            TextBlock(
                id=f"o{index}",
                bbox=rect,
                lines=[line],
                kind=_KIND_MAP.get(block.kind, BlockKind.PARAGRAPH),
            )
        )
    return PageLayout(number=number, width=width, height=height, blocks=text_blocks)


def _coords(raw: str) -> tuple[float, float, float, float] | None:
    parts = [part for part in re.split(r"[,\s]+", raw.strip()) if part]
    if len(parts) != 4:
        return None
    try:
        x0, y0, x1, y1 = (float(part) for part in parts)
    except ValueError:
        return None
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1, y1)
