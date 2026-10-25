"""Apici e pedici (Fase 1.3).

Un numero di nota è uno span più piccolo del resto della riga con la baseline spostata:
verso l'alto (apice) o verso il basso (pedice). Riconoscerlo evita due difetti:

* il blocco viene declassato a "corpo ridotto" perché lo span piccolo sembra testo che
  sfora;
* il riferimento di nota si fonde con la parola e si perde nel rendering.
"""

from __future__ import annotations

from pdfbook.domain.models import Line, Span, TextBlock

__all__ = [
    "SCRIPT_SCALE",
    "SMALL_RATIO",
    "SUBSCRIPT",
    "SUPERSCRIPT",
    "block_has_script",
    "dominant_size",
    "script_baseline_offset",
    "script_of",
    "script_scale",
]

SUPERSCRIPT = "sup"
SUBSCRIPT = "sub"

#: Uno span è "piccolo" sotto questa frazione del corpo dominante della riga.
SMALL_RATIO = 0.85
#: Scostamento minimo di baseline (frazione del corpo dominante) per parlare di apice/pedice.
RISE_RATIO = 0.10
#: Corpo dell'apice/pedice rispetto al corpo della riga.
SCRIPT_SCALE = 0.68


def dominant_size(line: Line) -> float:
    """Corpo più frequente della riga (pesato sui caratteri, non sugli span)."""
    weights: dict[float, int] = {}
    for span in line.spans:
        if span.size <= 0:
            continue
        key = round(span.size, 1)
        weights[key] = weights.get(key, 0) + max(len(span.text.strip()), 1)
    if not weights:
        return max((span.size for span in line.spans), default=0.0)
    return max(weights.items(), key=lambda item: (item[1], item[0]))[0]


def script_of(span: Span, line: Line) -> str | None:
    """``"sup"``, ``"sub"`` o ``None`` per lo span nella riga data."""
    base = dominant_size(line)
    if base <= 0 or span.size <= 0 or span.size > base * SMALL_RATIO:
        return None
    baseline = span.origin_y if span.origin_y is not None else line.origin_y
    offset = baseline - line.origin_y
    if offset < -base * RISE_RATIO:
        return SUPERSCRIPT
    if offset > base * RISE_RATIO:
        return SUBSCRIPT
    return None


def block_has_script(block: TextBlock) -> bool:
    """``True`` se il blocco contiene almeno un apice o un pedice."""
    return any(
        script_of(span, line) is not None for line in block.lines for span in line.spans
    )


def script_scale(script: str | None) -> float:
    """Fattore di corpo per apici e pedici (1.0 per il testo normale)."""
    return SCRIPT_SCALE if script else 1.0


def script_baseline_offset(script: str | None, size: float) -> float:
    """Spostamento di baseline in punti (negativo = più in alto)."""
    if script == SUPERSCRIPT:
        return -size * 0.33
    if script == SUBSCRIPT:
        return size * 0.16
    return 0.0
