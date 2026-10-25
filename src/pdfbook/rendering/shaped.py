"""Disegno di testo con shaping completo: RTL e CJK (Fase 4.5).

``TextWriter`` posiziona i glifi uno dopo l'altro: per arabo, ebraico, devanagari, cinese e
giapponese serve il **shaping** (forme contestuali, legature, direzione) che PyMuPDF offre
solo attraverso il motore HTML/CSS (``insert_htmlbox``).

Quindi: i blocchi in scritture non latine non passano dal painter di prosa, ma da un riquadro
HTML con ``dir`` corretto e una catena di font che include il bundle (Noto) quando c'è. Se il
font non copre i glifi il risultato resta visibile nel QA: il testo è comunque estraibile e
l'eventuale perdita finisce nei controlli già attivi.

Confine: qui si costruisce l'HTML e si chiede al canvas di inserirlo. Nessun ``fitz``.
"""

from __future__ import annotations

import html as html_lib
from dataclasses import dataclass

from pdfbook.domain.models import PageLayout, Rect, TextBlock

from .canvas import PageCanvas

__all__ = ["SHAPED_CSS", "ShapedResult", "direction_for", "paint_shaped"]

#: Catena di font: prima il bundle, poi i nomi di sistema più diffusi, poi un generico.
SHAPED_CSS = """
* {{
  font-family: {families};
  font-size: {size}pt;
  direction: {direction};
  text-align: {align};
  line-height: 1.3;
  margin: 0;
  padding: 0;
}}
"""

#: Famiglie per scrittura: il bundle Noto copre le necessità tipiche.
_FAMILIES = {
    "arabic": "'Noto Naskh Arabic', 'Amiri', 'Segoe UI', serif",
    "hebrew": "'Noto Sans Hebrew', 'David', 'Segoe UI', serif",
    "han": "'Noto Serif CJK SC', 'Source Han Serif', 'SimSun', serif",
    "kana": "'Noto Serif CJK JP', 'Yu Mincho', 'MS Mincho', serif",
    "hangul": "'Noto Serif CJK KR', 'Malgun Gothic', serif",
    "devanagari": "'Noto Sans Devanagari', 'Mangal', serif",
    "thai": "'Noto Sans Thai', 'Tahoma', serif",
}
_DEFAULT_FAMILIES = "'Noto Sans', 'DejaVu Sans', sans-serif"
_RTL = frozenset({"arabic", "hebrew"})


@dataclass(frozen=True)
class ShapedResult:
    """Esito del disegno di un blocco: se è andato, quanto spazio ha preso."""

    painted: bool
    y_end: float


def direction_for(system: str) -> str:
    return "rtl" if system in _RTL else "ltr"


def shaped_css(system: str, size: float) -> str:
    """CSS del riquadro, con famiglie e direzione della scrittura."""
    families = _FAMILIES.get(system, _DEFAULT_FAMILIES)
    direction = direction_for(system)
    align = "right" if direction == "rtl" else "left"
    return SHAPED_CSS.format(families=families, size=round(max(size, 4.0), 2), direction=direction, align=align)


def paint_shaped(
    block: TextBlock,
    page: PageLayout,
    text: str,
    *,
    system: str,
    canvas: PageCanvas,
    shift: float = 0.0,
) -> ShapedResult:
    """Inserisce il testo nel riquadro del blocco con shaping e direzione corretta."""
    box = Rect(block.bbox.x0, block.bbox.y0 + shift, block.bbox.x1, block.bbox.y1 + shift)
    body = html_lib.escape(text.replace("\n", " ")).strip()
    if not body:
        return ShapedResult(False, box.y0)
    markup = f'<div dir="{direction_for(system)}">{body}</div>'
    size = block.primary_span.size or 10.0
    try:
        placed = canvas.insert_markup(box, markup, shaped_css(system, size))
    except Exception:  # noqa: BLE001 - un blocco che non entra non deve fermare la pagina
        return ShapedResult(False, box.y0)
    return ShapedResult(bool(placed), box.y1 if placed else box.y0)
