"""Strutture dati del dominio.

Invarianti:
- tutte le misure sono in **punti PDF** (1/72 di pollice), come PyMuPDF;
- ``Rect`` è immutabile e normalizzata (x0 <= x1, y0 <= y1);
- un ``TextBlock`` contiene almeno una ``Line``; una ``Line`` almeno uno ``Span``;
- l'identità di un blocco (``id``) è stabile solo all'interno di una pagina:
  la chiave globale è ``page_id + ":" + block.id``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "BlockKind",
    "IssueKind",
    "Line",
    "PageLayout",
    "QAIssue",
    "QAReport",
    "Rect",
    "Span",
    "TextBlock",
    "TranslationSettings",
]


class BlockKind(StrEnum):
    """Natura tipografica di un blocco, dedotta dall'estrattore o dal segmentatore."""

    PARAGRAPH = "paragraph"
    TITLE = "title"
    TOC_ROW = "toc_row"
    LIST_ITEM = "list_item"
    TABLE_CELL = "table_cell"
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    FURNITURE = "furniture"
    UNKNOWN = "unknown"


class IssueKind(StrEnum):
    """Tipologie di problema registrabili nel QA report."""

    FONT_REDUCED = "font_reduced"
    RETRANSLATED = "retranslated"
    OVERFLOW_SHIFTED = "overflow_shifted"
    UNTRANSLATED_RECOVERED = "untranslated_recovered"
    UNTRANSLATED_UNRESOLVED = "untranslated_unresolved"
    GLYPH_MISSING = "glyph_missing"
    TEXT_OVERLAP = "text_overlap"
    CLIPPED = "clipped"
    TEXT_MISSING = "text_missing"
    SCAN_FALLBACK = "scan_fallback"
    VISUAL_DRIFT = "visual_drift"
    PARAGRAPH_STITCHED = "paragraph_stitched"
    SPLIT_FAILED = "split_failed"
    GLOSSARY_VIOLATION = "glossary_violation"
    TABLE_MISALIGNED = "table_misaligned"
    STYLE_FLATTENED = "style_flattened"
    LENGTH_RATIO = "length_ratio"
    REPETITION = "repetition"
    WRONG_LANGUAGE = "wrong_language"


@dataclass(frozen=True)
class Rect:
    """Rettangolo allineato agli assi, in punti PDF."""

    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self) -> None:
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError(f"Rect non normalizzata: {self.normalized()}")

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        return self.width * self.height

    def normalized(self) -> tuple[float, float, float, float]:
        return (self.x0, self.y0, self.x1, self.y1)

    def intersection(self, other: Rect) -> Rect | None:
        x0, y0 = max(self.x0, other.x0), max(self.y0, other.y0)
        x1, y1 = min(self.x1, other.x1), min(self.y1, other.y1)
        if x1 <= x0 or y1 <= y0:
            return None
        return Rect(x0, y0, x1, y1)

    def overlap_ratio(self, other: Rect) -> float:
        """Area di intersezione / area del più piccolo dei due (0.0 se disgiunti)."""
        inter = self.intersection(other)
        if inter is None:
            return 0.0
        smallest = min(self.area, other.area)
        return 0.0 if smallest <= 0 else inter.area / smallest

    def union(self, other: Rect) -> Rect:
        return Rect(
            min(self.x0, other.x0),
            min(self.y0, other.y0),
            max(self.x1, other.x1),
            max(self.y1, other.y1),
        )


@dataclass(frozen=True)
class Span:
    """Porzione di riga con font/dimensione/colore omogenei.

    ``origin_y`` è la baseline dello span (``None`` = sconosciuta: si usa quella della riga).
    Serve a riconoscere apici e pedici, che hanno baseline spostata rispetto alla riga.
    """

    text: str
    font_name: str = ""
    size: float = 0.0
    color: int = 0  # intero RGB come lo restituisce PyMuPDF
    origin_y: float | None = None

    def is_blank(self) -> bool:
        return not self.text.strip()


@dataclass
class Line:
    """Riga tipografica: insieme di span con la stessa baseline."""

    spans: list[Span]
    bbox: Rect
    origin_y: float

    def __post_init__(self) -> None:
        if not self.spans:
            raise ValueError("una Line richiede almeno uno Span")

    @property
    def text(self) -> str:
        return "".join(span.text for span in self.spans)

    @property
    def primary_span(self) -> Span:
        """Span che definisce font/dimensione/colore della riga (il primo)."""
        return self.spans[0]


@dataclass
class TextBlock:
    """Blocco di testo estratto da una pagina."""

    id: str
    bbox: Rect
    lines: list[Line]
    kind: BlockKind = BlockKind.UNKNOWN

    def __post_init__(self) -> None:
        if not self.lines:
            raise ValueError("un TextBlock richiede almeno una Line")

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines).strip()

    @property
    def line_count(self) -> int:
        return len(self.lines)

    @property
    def primary_span(self) -> Span:
        return self.lines[0].primary_span

    def global_key(self, page_number: int) -> str:
        return f"p{page_number}:{self.id}"


@dataclass
class PageLayout:
    """Una pagina estratta: blocchi di testo + ostacoli (immagini/grafica)."""

    number: int
    width: float
    height: float
    blocks: list[TextBlock] = field(default_factory=list)
    image_boxes: list[Rect] = field(default_factory=list)

    def text_blocks(self) -> list[TextBlock]:
        return [block for block in self.blocks if block.text]

    def blocks_overlapping(self, box: Rect) -> list[TextBlock]:
        return [block for block in self.blocks if block.bbox.intersection(box)]


@dataclass(frozen=True)
class TranslationSettings:
    """Impostazioni di una singola esecuzione di traduzione."""

    provider: str
    model: str
    target_lang: str = "Italiano"
    base_url: str = ""
    glossary: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider obbligatorio")
        if not self.model.strip():
            raise ValueError("model obbligatorio")

    def cache_partition(self) -> str:
        """Identità della configurazione: parte obbligatoria della chiave di cache (R11/M3).

        Include provider, modello, lingua e glossario: due esecuzioni con impostazioni
        diverse non devono MAI condividere una traduzione.
        """
        payload = json.dumps(
            {
                "provider": self.provider,
                "model": self.model,
                "target_lang": self.target_lang,
                "glossary": list(self.glossary),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def with_glossary(self, terms: list[str]) -> TranslationSettings:
        cleaned = tuple(sorted({t.strip() for t in terms if t.strip()}))
        return TranslationSettings(
            provider=self.provider,
            model=self.model,
            target_lang=self.target_lang,
            base_url=self.base_url,
            glossary=cleaned,
        )


@dataclass(frozen=True)
class QAIssue:
    """Singolo problema rilevato su una pagina."""

    page: int
    kind: IssueKind
    block: str | None = None
    detail: str = ""

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"page": self.page, "type": self.kind.value}
        if self.block is not None:
            payload["block"] = self.block
        if self.detail:
            payload["detail"] = self.detail
        return payload


@dataclass
class QAReport:
    """Raccolta di issue + contatori di sintesi per un'esecuzione."""

    issues: list[QAIssue] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)

    def add(self, issue: QAIssue) -> None:
        self.issues.append(issue)
        self.counters[issue.kind.value] = self.counters.get(issue.kind.value, 0) + 1

    def count(self, kind: IssueKind) -> int:
        return self.counters.get(kind.value, 0)

    def issues_for_page(self, page: int) -> list[QAIssue]:
        return [issue for issue in self.issues if issue.page == page]

    def to_dict(self) -> dict[str, object]:
        return {
            "pages": self._pages_payload(),
            "summary": dict(sorted(self.counters.items())),
        }

    def _pages_payload(self) -> list[dict[str, object]]:
        grouped: dict[int, list[dict[str, object]]] = {}
        for issue in self.issues:
            grouped.setdefault(issue.page, []).append(issue.to_dict())
        return [{"page": page, "issues": items} for page, items in sorted(grouped.items())]
