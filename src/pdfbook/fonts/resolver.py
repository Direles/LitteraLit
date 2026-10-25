"""Cascata di risoluzione dei font (M5).

Ordine di preferenza, con verifica dei glifi della lingua di destinazione:

1. **font embedded nel PDF** con lo stesso nome base (il migliore: identico all'originale);
2. **font embedded simile** (stessa famiglia normalizzata, stile compatibile);
3. **font di sistema** della famiglia/stile corrispondente;
4. ultima spiaggia: un base-14 (``helv``) — che però **non** copre tutti i caratteri
   tipografici, quindi va segnalato, non nascosto.

Il modulo è puro rispetto a PyMuPDF: la sorgente dei font e la factory dei font sono
iniettate (``fonts/fitz_adapter.py`` fornisce le implementazioni reali). Questo permette
di testare l'intera cascata senza aprire un PDF.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .bundled import BundledFonts, bundle_family_for
from .platform_fonts import classify, resolve_path

__all__ = [
    "LANG_TEST_CHARS",
    "EmbeddedFontSource",
    "FontResolver",
    "ResolverStats",
]

log = logging.getLogger(__name__)

# Caratteri che il font DEVE saper rendere per la lingua di destinazione.
LANG_TEST_CHARS: Mapping[str, str] = {
    "Italiano": "àèéìòùÀÈÉÌÒÙ'\"\u201c\u201d\u2019\u2014\u2013",
    "Spagnolo": "áéíóúñü¿¡ÁÉÍÓÚÑ",
    "Francese": "àâçéèêëîïôùûüœÀÇÉ",
    "Tedesco": "äöüßÄÖÜ",
    "Inglese": "'\"\u201c\u201d\u2019",
}

_WEAK_SUFFIXES = ("tot", "ot", "t")


@runtime_checkable
class EmbeddedFontSource(Protocol):
    """Accesso minimo al documento per estrarre i font embeddati."""

    @property
    def page_count(self) -> int: ...

    def page_fonts(self, page_index: int) -> Sequence[tuple[int, str]]: ...

    def extract_font(self, xref: int) -> tuple[str, str, str, bytes | None]: ...


@dataclass
class ResolverStats:
    """Contatori per il QA report: da dove arriva ogni font usato."""

    embedded_reused: int = 0
    fuzzy_reused: int = 0
    bundle_used: int = 0
    system_fallback: int = 0
    base14_fallback: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "embedded_reused": self.embedded_reused,
            "fuzzy_reused": self.fuzzy_reused,
            "bundle_used": self.bundle_used,
            "system_fallback": self.system_fallback,
            "base14_fallback": self.base14_fallback,
        }


def _normalize(base: str) -> tuple[str, str]:
    """``(famiglia, nome completo)`` senza prefisso subset e suffissi tecnici."""
    full = base.lower().split("+")[-1]
    family = full.split("-")[0]
    for suffix in _WEAK_SUFFIXES:
        if family.endswith(suffix) and len(family) - len(suffix) >= 6:
            family = family[: -len(suffix)]
            break
    return family, full


def _style(full: str) -> tuple[bool, bool, bool]:
    """``(bold, italic, narrow)`` dedotti dal nome completo."""
    bold = "bold" in full or "medium" in full
    italic = "italic" in full or "obli" in full
    narrow = "nar" in full or "cond" in full
    return bold, italic, narrow


def _fuzzy_score(target: tuple[bool, bool, bool], candidate: tuple[bool, bool, bool]) -> int:
    score = 1
    score += 2 if candidate[0] == target[0] else 0
    score += 2 if candidate[1] == target[1] else 0
    score += 1 if candidate[2] == target[2] else 0
    return score


class FontResolver:
    """Risolve un nome font PDF in un oggetto font utilizzabile per misurare e disegnare."""

    def __init__(
        self,
        source: EmbeddedFontSource | None = None,
        *,
        font_factory: Callable[..., Any],
        target_lang: str = "Italiano",
        platform: str | None = None,
        exists: Callable[[str], bool] | None = None,
        base14_name: str = "helv",
        bundle: BundledFonts | None = None,
    ) -> None:
        self.source = source
        self.font_factory = font_factory
        self.test_chars = LANG_TEST_CHARS.get(target_lang, LANG_TEST_CHARS["Italiano"])
        self.platform = platform
        self.exists = exists
        self.base14_name = base14_name
        self.bundle = bundle
        self.stats = ResolverStats()
        self._embedded: dict[str, bytes] = {}
        self._cache: dict[str, Any] = {}
        self._seen_xrefs: set[int] = set()
        self._extracted = False

    # ---------- API ----------

    def resolve(self, pdf_font_name: str) -> Any:
        """Font migliore disponibile per ``pdf_font_name`` (con cache per nome)."""
        if pdf_font_name in self._cache:
            return self._cache[pdf_font_name]
        font, origin = self._resolve_uncached(pdf_font_name)
        self._count(origin)
        self._cache[pdf_font_name] = font
        return font

    def _count(self, origin: str) -> None:
        if origin == "embedded_reused":
            self.stats.embedded_reused += 1
        elif origin == "fuzzy_reused":
            self.stats.fuzzy_reused += 1
        elif origin == "bundle_used":
            self.stats.bundle_used += 1
        elif origin == "system_fallback":
            self.stats.system_fallback += 1
        else:
            self.stats.base14_fallback += 1

    def text_length(self, text: str, pdf_font_name: str, fontsize: float) -> float:
        """Larghezza reale del testo con il font risolto (metriche, non stime)."""
        return float(self.resolve(pdf_font_name).text_length(text, fontsize=fontsize))

    def covered(self, pdf_font_name: str) -> bool:
        """``True`` se il font risolto copre i caratteri della lingua di destinazione."""
        return self._coverage_ok(self.resolve(pdf_font_name))

    # ---------- interno ----------

    def _resolve_uncached(self, pdf_font_name: str) -> tuple[Any, str]:
        base = pdf_font_name.split("+")[-1]
        embedded = self._embedded_for(base)
        if embedded is not None:
            font = self._make(buffer=embedded)
            if font is not None and self._coverage_ok(font):
                return font, "embedded_reused" if base in self._embedded else "fuzzy_reused"
        font = self._bundle_font(pdf_font_name)
        if font is not None:
            return font, "bundle_used"
        font = self._system_font(pdf_font_name)
        if font is not None:
            return font, "system_fallback"
        log.warning("nessun font di sistema per %s: uso %s", pdf_font_name, self.base14_name)
        return self._make(name=self.base14_name), "base14_fallback"

    def _embedded_for(self, base: str) -> bytes | None:
        self._ensure_extracted()
        if base in self._embedded:
            return self._embedded[base]
        return self._fuzzy_match(base)

    def _ensure_extracted(self) -> None:
        if self._extracted or self.source is None:
            self._extracted = True
            return
        for page_index in range(self.source.page_count):
            for xref, _name in self.source.page_fonts(page_index):
                if xref in self._seen_xrefs:
                    continue
                self._seen_xrefs.add(xref)
                try:
                    name, ext, _kind, buffer = self.source.extract_font(xref)
                except Exception as exc:  # noqa: BLE001 - font illeggibile: si prosegue
                    log.debug("font xref %s non estraibile: %s", xref, exc)
                    continue
                if buffer and ext in ("ttf", "otf", "cff"):
                    self._embedded.setdefault(name.split("+")[-1], buffer)
        self._extracted = True

    def _fuzzy_match(self, base: str) -> bytes | None:
        family, full = _normalize(base)
        target = _style(full)
        best: bytes | None = None
        best_score = 0
        for name, buffer in self._embedded.items():
            other_family, other_full = _normalize(name)
            if other_family != family:
                continue
            score = _fuzzy_score(target, _style(other_full))
            if score > best_score:
                best, best_score = buffer, score
        return best

    def _coverage_ok(self, font: Any) -> bool:
        try:
            return all(font.has_glyph(ord(char)) > 0 for char in self.test_chars)
        except Exception:  # noqa: BLE001 - font che non espone has_glyph: prudenza
            return False

    def _bundle_font(self, pdf_font_name: str) -> Any | None:
        """Font del bundle (se installato) compatibile con il nome PDF."""
        if self.bundle is None:
            return None
        family = bundle_family_for(pdf_font_name, self.bundle)
        if family is None:
            return None
        _family_class, bold, italic = classify(pdf_font_name)
        path = self.bundle.path_for(family, bold, italic)
        if not path:
            return None
        font = self._make(path=path)
        if font is None or not self._coverage_ok(font):
            return None
        return font

    def _system_font(self, pdf_font_name: str) -> Any | None:
        family, bold, italic = classify(pdf_font_name)
        kwargs: dict[str, Any] = {"platform": self.platform}
        if self.exists is not None:
            kwargs["exists"] = self.exists
        path = resolve_path(family, bold, italic, **kwargs)
        if not path:
            return None
        return self._make(path=path)

    def _make(self, *, buffer: bytes | None = None, path: str | None = None, name: str | None = None) -> Any | None:
        try:
            return self.font_factory(buffer=buffer, path=path, name=name)
        except Exception as exc:  # noqa: BLE001 - un font rotto non deve fermare il libro
            log.debug("font non caricabile (%s): %s", path or name or "buffer", exc)
            return None
