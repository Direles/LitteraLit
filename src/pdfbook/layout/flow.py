"""Paragraph stitching fra pagine (Fase 2).

Problema reale: un paragrafo che continua a pagina successiva viene tradotto come due
frammenti indipendenti, quindi con concordanze e maiuscole incoerenti. Qui si rileva la
continuazione, si unisce il testo per la traduzione e — dopo la traduzione — lo si
ridistribuisce sui due blocchi originali, mantenendo il layout.

Le euristiche sono **conservative**: meglio non unire che unire due paragrafi estranei
(un errore di questo tipo è molto più visibile di una frase spezzata).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pdfbook.domain.models import BlockKind, PageLayout, TextBlock

from .segmentation import classify_block

__all__ = [
    "Continuation",
    "SplitResult",
    "detect_continuations",
    "merged_text",
    "split_translation",
]

TERMINAL = ".!?:;\u2026"
CLOSERS = "\"'\u201d\u2019\u00bb)]}"
MIN_CHARS = 20
MIN_X_OVERLAP = 0.5
MAX_X_DRIFT = 24.0
TOP_ZONE = 0.35
SENTENCE_BREAKS = ".!?;\u2026"
MIN_PART = 0.20
SPLIT_WINDOW = 0.18
_STITCHABLE_KINDS = {BlockKind.PARAGRAPH, BlockKind.UNKNOWN}


@dataclass(frozen=True)
class Continuation:
    """Un blocco che prosegue su una pagina successiva."""

    previous_index: int
    previous_block: str
    next_index: int
    next_block: str
    hyphen: bool = False

    @property
    def key(self) -> str:
        return f"p{self.previous_index}:{self.previous_block}+p{self.next_index}:{self.next_block}"


@dataclass(frozen=True)
class SplitResult:
    """Ridistribuzione della traduzione sui due blocchi."""

    first: str
    second: str
    exact: bool

    @property
    def usable(self) -> bool:
        return bool(self.first) and bool(self.second)


def detect_continuations(pages: Sequence[PageLayout]) -> list[Continuation]:
    """Coppie (ultimo blocco di una pagina, primo della successiva) che continuano."""
    continuations: list[Continuation] = []
    for index in range(len(pages) - 1):
        previous = _edge_block(pages[index], last=True)
        following = _edge_block(pages[index + 1], last=False)
        if previous is None or following is None:
            continue
        if not _is_continuation(previous, following, pages[index + 1]):
            continue
        text = previous.text.rstrip()
        continuations.append(
            Continuation(
                previous_index=index,
                previous_block=previous.id,
                next_index=index + 1,
                next_block=following.id,
                hyphen=text.endswith(("-\u2010", "\u2010", "-")),
            )
        )
    return continuations


def merged_text(previous: TextBlock, following: TextBlock, *, hyphen: bool) -> str:
    """Testo unico da tradurre: con il trattino si unisce senza spazio."""
    left = previous.text.rstrip()
    right = following.text.strip()
    if hyphen:
        return left.rstrip("-\u2010") + right
    return f"{left} {right}"


def split_translation(first: str, second: str, translated: str) -> SplitResult:
    """Divide la traduzione in due parti proporzionali all'originale, su un confine naturale."""
    text = translated.strip()
    if not text:
        return SplitResult("", "", False)
    total = max(len(first) + len(second), 1)
    target = int(len(first) / total * len(text))
    boundary = _best_boundary(text, target)
    if boundary is None:
        return SplitResult(text, "", False)
    left = text[:boundary].strip()
    right = text[boundary:].strip()
    smallest = min(len(left), len(right))
    if smallest < MIN_PART * len(text):
        return SplitResult(text, "", False)
    exact = text[boundary - 1] in SENTENCE_BREAKS
    return SplitResult(left, right, exact)


def _is_continuation(previous: TextBlock, following: TextBlock, next_page: PageLayout) -> bool:
    previous_text = previous.text.strip()
    if len(previous_text) < MIN_CHARS:
        return False
    stripped = previous_text.rstrip(CLOSERS).rstrip()
    if not stripped or stripped[-1] in TERMINAL:
        return False
    letters = [char for char in following.text.strip() if char.isalpha()]
    if not letters or not letters[0].islower():
        return False
    if classify_block(previous).kind not in _STITCHABLE_KINDS:
        return False
    if classify_block(following).kind not in _STITCHABLE_KINDS:
        return False
    if following.bbox.y0 > next_page.height * TOP_ZONE:
        return False
    return _x_overlap(previous, following) >= MIN_X_OVERLAP


def _x_overlap(previous: TextBlock, following: TextBlock) -> float:
    left = max(previous.bbox.x0, following.bbox.x0)
    right = min(previous.bbox.x1, following.bbox.x1)
    if right <= left:
        return 0.0
    narrowest = min(previous.bbox.width, following.bbox.width)
    if narrowest <= 0:
        return 0.0
    if abs(previous.bbox.x0 - following.bbox.x0) <= MAX_X_DRIFT:
        return max((right - left) / narrowest, MIN_X_OVERLAP)
    return (right - left) / narrowest


def _edge_block(page: PageLayout, *, last: bool) -> TextBlock | None:
    blocks = [block for block in page.blocks if block.text.strip()]
    if not blocks:
        return None
    picker = max if last else min
    return picker(blocks, key=lambda block: block.bbox.y0)


def _best_boundary(text: str, target: int) -> int | None:
    """Confine di parola (preferendo fine frase) più vicino al punto proporzionale."""
    if not text:
        return None
    span = max(int(len(text) * SPLIT_WINDOW), 1)
    low, high = max(target - span, 1), min(target + span, len(text) - 1)
    if low >= high:
        return None
    sentence = _nearest(text, low, high, target, sentence_only=True)
    if sentence is not None:
        return sentence
    return _nearest(text, low, high, target, sentence_only=False)


def _nearest(text: str, low: int, high: int, target: int, *, sentence_only: bool) -> int | None:
    best: int | None = None
    for position in range(low, high + 1):
        if text[position - 1] == " " or text[position] != " ":
            continue
        if sentence_only and text[position - 1] not in SENTENCE_BREAKS:
            continue
        if best is None or abs(position - target) < abs(best - target):
            best = position
    return best
