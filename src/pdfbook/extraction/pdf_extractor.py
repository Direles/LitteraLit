"""Da ``page.get_text('dict')`` a ``PageLayout`` (M8).

Regole:

- **solo geometria e testo**: nessuna classificazione (è di ``layout.segmentation``) e
  nessun disegno (è di ``rendering``);
- blocchi non testuali diventano ``image_boxes``: sono ostacoli per il fitting;
- i dati malformati non fermano il libro: la riga/blocco viene scartato e si prosegue;
- le coordinate restano in punti PDF, come PyMuPDF.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pdfbook.domain.models import Line, PageLayout, Rect, Span, TextBlock

__all__ = [
    "block_from_raw",
    "extract_page",
    "image_box",
    "is_text_block",
    "line_from_raw",
    "span_from_raw",
]

_ORIGIN_FALLBACK_RATIO = 0.2


def span_from_raw(raw: Mapping[str, Any]) -> Span:
    """Converte uno span di PyMuPDF; campi assenti → valori neutri."""
    return Span(
        text=str(raw.get("text", "")),
        font_name=str(raw.get("font", "")),
        size=float(raw.get("size", 0.0) or 0.0),
        color=int(raw.get("color", 0) or 0),
    )


def line_from_raw(raw: Mapping[str, Any]) -> Line | None:
    """Converte una riga; ``None`` se vuota (anche solo spazi) o con bbox non valida."""
    spans = [span_from_raw(span) for span in raw.get("spans") or []]
    spans = [span for span in spans if span.text]
    if not spans or not any(span.text.strip() for span in spans):
        return None
    box = _rect(raw.get("bbox"))
    if box is None:
        return None
    origin = _origin(raw)
    if origin is None:
        origin = box.y1 - max(spans[0].size, 0.0) * _ORIGIN_FALLBACK_RATIO
    return Line(spans=spans, bbox=box, origin_y=origin)


def block_from_raw(raw: Mapping[str, Any], index: int = 0) -> TextBlock | None:
    """Converte un blocco di testo; ``None`` se non contiene righe valide."""
    lines = [line for line in (line_from_raw(item) for item in raw.get("lines") or []) if line]
    if not lines:
        return None
    box = _rect(raw.get("bbox"))
    if box is None:
        box = _bounding_box(lines)
    if box is None:
        return None
    return TextBlock(id=f"b{index}", bbox=box, lines=lines)


def image_box(raw: Mapping[str, Any]) -> Rect | None:
    """Bbox di un blocco non testuale, se valida."""
    return _rect(raw.get("bbox"))


def is_text_block(raw: Mapping[str, Any]) -> bool:
    """``True`` per i blocchi testuali (``type == 0``)."""
    return int(raw.get("type", 0) or 0) == 0


def extract_page(
    raw_page: Mapping[str, Any],
    *,
    number: int,
    width: float,
    height: float,
) -> PageLayout:
    """Costruisce la pagina: blocchi di testo numerati + ostacoli (immagini/grafica)."""
    blocks: list[TextBlock] = []
    obstacles: list[Rect] = []
    for raw in raw_page.get("blocks") or []:
        if not isinstance(raw, Mapping):
            continue
        if not is_text_block(raw):
            box = image_box(raw)
            if box is not None:
                obstacles.append(box)
            continue
        block = block_from_raw(raw, index=len(blocks))
        if block is not None:
            blocks.append(block)
    return PageLayout(
        number=number,
        width=float(width),
        height=float(height),
        blocks=blocks,
        image_boxes=obstacles,
    )


def _rect(value: Any) -> Rect | None:
    """Accetta sequenze di 4 numeri; ``None`` se non valida."""
    if not isinstance(value, (tuple, list)) or len(value) < 4:
        return None
    try:
        x0, y0, x1, y1 = (float(part) for part in value[:4])
        return Rect(x0, y0, x1, y1)
    except (TypeError, ValueError):
        return None


def _origin(raw: Mapping[str, Any]) -> float | None:
    for span in raw.get("spans") or []:
        origin = span.get("origin")
        if isinstance(origin, Sequence) and len(origin) >= 2:
            try:
                return float(origin[1])
            except (TypeError, ValueError):
                return None
    return None


def _bounding_box(lines: Sequence[Line]) -> Rect | None:
    try:
        return Rect(
            min(line.bbox.x0 for line in lines),
            min(line.bbox.y0 for line in lines),
            max(line.bbox.x1 for line in lines),
            max(line.bbox.y1 for line in lines),
        )
    except ValueError:
        return None
