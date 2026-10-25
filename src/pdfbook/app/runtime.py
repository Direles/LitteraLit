"""Costruzione delle dipendenze reali di un job (M11).

``Runtime`` è il punto in cui si incontrano PyMuPDF, provider, cache, font e canvas.
Nei test si sostituisce l'intero oggetto: la pipeline non sa (e non deve sapere) che cosa
ci sia dietro.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pdfbook.config.settings import AppSettings
from pdfbook.extraction.fitz_source import PdfPageSource
from pdfbook.fonts.bundled import BundledFonts
from pdfbook.fonts.fitz_adapter import PdfFontSource, make_fitz_font
from pdfbook.fonts.resolver import FontResolver
from pdfbook.rendering.fitz_canvas import FitzCanvas
from pdfbook.translation.cache import TranslationCache
from pdfbook.translation.providers.registry import create_provider

__all__ = ["Runtime", "build_runtime"]

log = logging.getLogger(__name__)


@dataclass
class Runtime:
    """Dipendenze di un job, già pronte (o finte, nei test)."""

    source: Any
    provider: Any
    cache: TranslationCache
    resolver: Any
    canvas_factory: Callable[[int], Any]
    save: Callable[[str], None]
    close: Callable[[], None]
    stats: Callable[[], dict[str, int]]


def build_runtime(input_pdf: str | os.PathLike[str], settings: AppSettings) -> Runtime:
    """Apre il PDF e costruisce provider, cache, resolver e canvas reali."""
    source = PdfPageSource.open(str(input_pdf))
    font_source = PdfFontSource(source.doc)
    resolver = FontResolver(
        font_source,
        font_factory=make_fitz_font,
        target_lang=settings.target_lang,
        bundle=BundledFonts.discover(),
    )
    provider = create_provider(settings.translation_settings(), settings.api_key)
    cache = TranslationCache.for_settings(settings.cache_path, settings.translation_settings())

    def save(path: str) -> None:
        target = Path(path)
        temp = target.with_name(target.name + ".tmp")
        try:
            source.doc.subset_fonts()
        except Exception as exc:  # noqa: BLE001 - il subsetting è un'ottimizzazione
            log.warning("subset_fonts non riuscito: %s", exc)
        source.doc.save(str(temp), deflate=True, garbage=3)
        os.replace(temp, target)

    return Runtime(
        source=source,
        provider=provider,
        cache=cache,
        resolver=resolver,
        canvas_factory=lambda index: FitzCanvas(source.doc[index]),
        save=save,
        close=source.close,
        stats=lambda: {
            "embedded_fonts_reused": resolver.stats.embedded_reused + resolver.stats.fuzzy_reused,
            "system_fonts_used": resolver.stats.system_fallback,
            "bundle_fonts_used": resolver.stats.bundle_used,
            "base14_fallback": resolver.stats.base14_fallback,
        },
    )
