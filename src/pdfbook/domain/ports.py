"""Contratti tra moduli (regola R6).

Solo ``Protocol`` e tipi: nessuna implementazione, nessun import esterno al dominio.
Le implementazioni concrete (provider LLM, resolver font, renderer) vivono nei rispettivi
layer e vengono iniettate dal chiamante — mai importate per effetto collaterale.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from .models import PageLayout, QAIssue, Rect, Span, TextBlock

__all__ = [
    "DocumentSource",
    "FontHandle",
    "FontResolverPort",
    "ProgressPort",
    "RendererPort",
    "ShortenerPort",
    "TranslatorPort",
]


@runtime_checkable
class DocumentSource(Protocol):
    """Sorgente di pagine già estratte (PDF nativo, OCR, fixture di test)."""

    @property
    def page_count(self) -> int: ...

    def page(self, index: int) -> PageLayout: ...


@runtime_checkable
class TranslatorPort(Protocol):
    """Traduce un batch ``{chiave_blocco: testo}`` restituendo lo stesso schema."""

    def translate(
        self,
        batch: Mapping[str, str],
        context: str | None = None,
    ) -> dict[str, str]: ...


@runtime_checkable
class ShortenerPort(Protocol):
    """Riscrive una traduzione entro un budget di caratteri (feedback del layout)."""

    def shorten(self, original: str, current: str, max_chars: int) -> str: ...


@runtime_checkable
class FontHandle(Protocol):
    """Sottoinsieme delle capacità di ``fitz.Font`` usate dal layout."""

    def text_length(self, text: str, fontsize: float) -> float: ...

    def has_glyph(self, char_code: int) -> int: ...


@runtime_checkable
class FontResolverPort(Protocol):
    """Risolve il nome font del PDF in un font utilizzabile per il rendering."""

    def resolve(self, pdf_font_name: str) -> FontHandle: ...


class ProgressPort(Protocol):
    """Sink di avanzamento; le implementazioni devono essere thread-safe o bufferizzate."""

    def __call__(self, current: int, total: int, message: str) -> None: ...


@runtime_checkable
class RendererPort(Protocol):
    """Scrive il testo tradotto al posto dell'originale, restituendo le issue rilevate."""

    def render_page(
        self,
        page: PageLayout,
        translations: Mapping[str, str],
    ) -> Sequence[QAIssue]: ...


@runtime_checkable
class BlockClassifier(Protocol):
    """Classifica un blocco (prosa, titolo, riga d'indice, cella...)."""

    def classify(self, block: TextBlock, page_area: Rect) -> TextBlock: ...


@runtime_checkable
class SpanMetrics(Protocol):
    """Metriche di un singolo span, utili per stimare densità e corpo del testo."""

    def measure(self, span: Span, box: Rect) -> float: ...
