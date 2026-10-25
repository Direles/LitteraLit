"""Fitting tipografico (M6): a capo, sillabazione, scelta del corpo.

Riprende l'algoritmo validato sul campo della Gen 2 con tre differenze strutturali:

1. **nessun riferimento a font o PDF**: si usa ``measure(text, size) -> larghezza``,
   quindi il modulo è puro e testabile con metriche finte (R6);
2. i limiti (60% del corpo, minimo 6 pt, interlinea 1.25) sono costanti nominate;
3. il risultato dichiara esplicitamente se il testo **entra** nelle righe originali,
   invece di lasciare che il chiamante interpreti un flag ambiguo (§11.2/8).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pdfbook.domain.models import Rect

from .hyphenation import Hyphenation
from .toc import optimize_toc_line

__all__ = [
    "LINE_HEIGHT_FACTOR",
    "MIN_FONT_FRACTION",
    "MIN_FONT_SIZE",
    "SIZE_STEP",
    "FitResult",
    "estimate_max_chars",
    "fit_text",
    "wrap_text",
]

MIN_FONT_FRACTION = 0.60
MIN_FONT_SIZE = 6.0
LINE_HEIGHT_FACTOR = 1.25
SIZE_STEP = 0.5

Measure = Callable[[str, float], float]


@dataclass(frozen=True)
class FitResult:
    """Esito del fitting: corpo scelto, righe prodotte, se rispetta il vincolo di righe."""

    size: float
    lines: tuple[str, ...]
    fits: bool

    @property
    def line_height(self) -> float:
        return self.size * LINE_HEIGHT_FACTOR

    def height(self) -> float:
        return len(self.lines) * self.line_height

    def reduced_compared_to(self, target_size: float) -> bool:
        return self.size < target_size - 0.25


def wrap_text(
    text: str,
    *,
    measure: Measure,
    size: float,
    max_width: float,
    hyphenation: Hyphenation | None = None,
) -> list[str]:
    """Manda a capo il testo sulle metriche reali, con sillabazione opzionale."""

    def width(chunk: str) -> float:
        return measure(chunk, size)

    lines: list[str] = []
    for paragraph in text.split("\n"):
        candidate = optimize_toc_line(paragraph, measure=width, max_width=max_width)
        if width(candidate) <= max_width:
            lines.append(candidate)
            continue
        lines.extend(_wrap_paragraph(candidate, width, max_width, hyphenation))
    return lines


def _wrap_paragraph(
    paragraph: str,
    width: Callable[[str], float],
    max_width: float,
    hyphenation: Hyphenation | None,
) -> list[str]:
    current: list[str] = []
    lines: list[str] = []
    for word in paragraph.split(" "):
        if width(" ".join([*current, word])) <= max_width:
            current.append(word)
            continue
        prefix = " ".join(current) + (" " if current else "")
        split = None
        if hyphenation is not None:
            split = hyphenation.split_for_width(word, width, max_width - width(prefix))
        if split is not None:
            lines.append(" ".join([*current, split[0]]))
            current = [split[1]]
        elif current:
            lines.append(" ".join(current))
            current = [word]
        else:
            lines.append(word)
            current = []
    if current:
        lines.append(" ".join(current))
    return lines


def fit_text(
    text: str,
    *,
    measure: Measure,
    max_width: float,
    target_size: float,
    max_lines: int,
    bounds: Rect,
    obstacles: Sequence[Rect] = (),
    hyphenation: Hyphenation | None = None,
    min_fraction: float = MIN_FONT_FRACTION,
    min_size: float = MIN_FONT_SIZE,
    overflow_policy: str = "keep_size",
) -> FitResult:
    """Corpo più grande che rispetta ``max_lines`` senza invadere gli ostacoli.

    Se nessun corpo entra, ``overflow_policy`` decide cosa fare:

    - ``keep_size`` (default, comportamento storico): mantiene il corpo originale e
      lascia sbordare il testo — leggibile, ma può invadere il blocco successivo;
    - ``shrink``: scende al minimo (60%/6 pt) per ridurre l'invasione, sacrificando
      la leggibilità. Il chiamante riceve ``fits=False`` in entrambi i casi.
    """
    floor = max(target_size * min_fraction, min_size)
    fallback: tuple[float, list[str]] | None = None
    size = target_size
    while size >= floor:
        lines = wrap_text(
            text, measure=measure, size=size, max_width=max_width, hyphenation=hyphenation
        )
        overflow = _overlaps(bounds, len(lines) * size * LINE_HEIGHT_FACTOR, obstacles)
        if not overflow and len(lines) <= max_lines:
            return FitResult(size=size, lines=tuple(lines), fits=True)
        if not overflow and fallback is None:
            fallback = (size, lines)
        size -= SIZE_STEP

    if fallback is not None and overflow_policy == "keep_size":
        return FitResult(size=fallback[0], lines=tuple(fallback[1]), fits=False)
    lines = wrap_text(
        text, measure=measure, size=floor, max_width=max_width, hyphenation=hyphenation
    )
    return FitResult(size=floor, lines=tuple(lines), fits=False)


def _overlaps(bounds: Rect, height: float, obstacles: Sequence[Rect]) -> bool:
    area = Rect(bounds.x0, bounds.y0, bounds.x1, bounds.y0 + max(height, 0.0))
    return any(area.intersection(obstacle) is not None for obstacle in obstacles)


def estimate_max_chars(
    measure: Measure,
    *,
    size: float,
    max_width: float,
    num_lines: int,
    sample: str,
    safety: float = 0.95,
    sample_limit: int = 200,
) -> int:
    """Quanti caratteri entrano nel blocco alle metriche correnti (per la ritraduzione)."""
    probe = (sample or "abcdefghilmnopqrstuvz aeiou")[:sample_limit]
    if not probe:
        return 0
    width = measure(probe, size)
    if width <= 0:
        return 0
    per_line = max_width / (width / len(probe))
    return int(per_line * max(num_lines, 1) * safety)
