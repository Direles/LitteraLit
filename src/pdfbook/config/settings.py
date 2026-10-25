"""Configurazione applicativa (M11).

Regola non negoziabile: **la chiave API non viene mai salvata su disco** (R11). Si legge
da variabili d'ambiente o da un ``.env`` locale non versionato; l'oggetto settings è
immutabile e la sua rappresentazione non espone il segreto.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from pdfbook.domain.models import TranslationSettings

__all__ = [
    "DEFAULT_CACHE_PATH",
    "LANGUAGES",
    "LOG_LEVELS",
    "MODEL_SUGGESTIONS",
    "AppSettings",
    "load_env_file",
    "load_settings",
    "parse_glossary",
]

DEFAULT_CACHE_PATH = Path.home() / ".cache" / "pdfbook" / "translations_cache.json"
LANGUAGES = ("Italiano", "Inglese", "Spagnolo", "Francese", "Tedesco")
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

# Suggerimenti per la GUI: il modello resta modificabile a mano (i nomi cambiano spesso).
MODEL_SUGGESTIONS: dict[str, tuple[str, ...]] = {
    "Google Gemini": ("gemini-2.5-flash", "gemini-2.5-pro"),
    "OpenAI": ("gpt-4o-mini", "gpt-4o"),
    "DeepSeek": ("deepseek-chat", "deepseek-reasoner"),
    "Anthropic Claude": ("claude-sonnet-4-5", "claude-haiku-4-5"),
    "Custom OpenAI-Compatible": ("default",),
}
_REQUIRES_KEY = {"Google Gemini", "OpenAI", "DeepSeek", "Anthropic Claude"}
_REQUIRES_BASE_URL = {"Custom OpenAI-Compatible"}


@dataclass(frozen=True)
class AppSettings:
    """Impostazioni di una sessione: provider, modello, lingua, glossario, cache."""

    provider: str = "DeepSeek"
    model: str = "deepseek-chat"
    target_lang: str = "Italiano"
    base_url: str = ""
    glossary: tuple[str, ...] = ()
    cache_path: Path = DEFAULT_CACHE_PATH
    log_level: str = "INFO"
    ocr_url: str = ""
    api_key: str = field(default="", repr=False)
    visual_qa: bool = True
    visual_qa_dpi: float = 72.0
    stitch_paragraphs: bool = True
    checkpoint_every: int = 10
    workers: int = 1
    rate_limit: float = 0.0
    max_cost: float = 0.0
    inline_styles: bool = True
    reading_order: bool = True
    style: str = "fedele"

    def __post_init__(self) -> None:
        if self.target_lang not in LANGUAGES:
            raise ValueError(f"lingua non supportata: {self.target_lang}")
        if self.log_level.upper() not in LOG_LEVELS:
            raise ValueError(f"livello di log non valido: {self.log_level}")

    def translation_settings(self) -> TranslationSettings:
        return TranslationSettings(
            provider=self.provider,
            model=self.model,
            target_lang=self.target_lang,
            base_url=self.base_url,
            glossary=self.glossary,
            style=self.style,
        )

    def missing_required(self) -> tuple[str, ...]:
        """Campi obbligatori assenti (usato dalla CLI e dalla GUI prima di partire)."""
        missing: list[str] = []
        if self.provider in _REQUIRES_KEY and not self.api_key.strip():
            missing.append("PDFBOOK_API_KEY")
        if self.provider in _REQUIRES_BASE_URL and not self.base_url.strip():
            missing.append("PDFBOOK_BASE_URL")
        return tuple(missing)

    def redacted(self) -> dict[str, object]:
        """Rappresentazione sicura per log e diagnostica: la chiave è un booleano."""
        return {
            "provider": self.provider,
            "model": self.model,
            "target_lang": self.target_lang,
            "base_url": self.base_url,
            "glossary": list(self.glossary),
            "cache_path": str(self.cache_path),
            "log_level": self.log_level,
            "ocr_url": self.ocr_url,
            "visual_qa": self.visual_qa,
            "visual_qa_dpi": self.visual_qa_dpi,
            "stitch_paragraphs": self.stitch_paragraphs,
            "checkpoint_every": self.checkpoint_every,
            "workers": self.workers,
            "rate_limit": self.rate_limit,
            "max_cost": self.max_cost,
            "inline_styles": self.inline_styles,
            "reading_order": self.reading_order,
            "style": self.style,
            "has_api_key": bool(self.api_key),
        }


def parse_glossary(raw: str) -> tuple[str, ...]:
    """Termini separati da virgola: trim, scarta vuoti, deduplica mantenendo l'ordine."""
    seen: dict[str, None] = {}
    for term in raw.split(","):
        cleaned = term.strip()
        if cleaned:
            seen.setdefault(cleaned, None)
    return tuple(seen)


def load_env_file(path: str | os.PathLike[str]) -> dict[str, str]:
    """Legge un ``.env`` minimale (``CHIAVE=valore``, commenti con ``#``)."""
    file_path = Path(path)
    if not file_path.exists():
        return {}
    values: dict[str, str] = {}
    for line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_settings(
    env: Mapping[str, str] | None = None,
    *,
    env_file: str | os.PathLike[str] | None = None,
) -> AppSettings:
    """Costruisce le impostazioni: file ``.env`` come base, variabili d'ambiente vincenti."""
    source: dict[str, str] = dict(load_env_file(env_file)) if env_file else {}
    source.update(dict(os.environ if env is None else env))
    cache = source.get("PDFBOOK_CACHE_PATH", "").strip() or str(DEFAULT_CACHE_PATH)
    return AppSettings(
        provider=source.get("PDFBOOK_PROVIDER", "DeepSeek").strip() or "DeepSeek",
        model=source.get("PDFBOOK_MODEL", "deepseek-chat").strip() or "deepseek-chat",
        target_lang=source.get("PDFBOOK_TARGET_LANG", "Italiano").strip() or "Italiano",
        base_url=source.get("PDFBOOK_BASE_URL", "").strip(),
        glossary=parse_glossary(source.get("PDFBOOK_GLOSSARY", "")),
        cache_path=Path(cache).expanduser(),
        log_level=(source.get("PDFBOOK_LOG_LEVEL", "INFO").strip() or "INFO").upper(),
        ocr_url=source.get("PDFBOOK_OCR_URL", "").strip(),
        api_key=source.get("PDFBOOK_API_KEY", ""),
        visual_qa=_as_bool(source.get("PDFBOOK_VISUAL_QA", "1")),
        visual_qa_dpi=_as_float(source.get("PDFBOOK_VISUAL_QA_DPI", "72"), 72.0),
        stitch_paragraphs=_as_bool(source.get("PDFBOOK_STITCH", "1")),
        checkpoint_every=int(_as_float(source.get("PDFBOOK_CHECKPOINT_EVERY", "10"), 10.0)),
        workers=int(_as_float(source.get("PDFBOOK_WORKERS", "1"), 1.0)),
        rate_limit=_as_float(source.get("PDFBOOK_RATE_LIMIT", "0"), 0.0),
        max_cost=_as_float(source.get("PDFBOOK_MAX_COST", "0"), 0.0),
        inline_styles=_as_bool(source.get("PDFBOOK_INLINE_STYLES", "1")),
        reading_order=_as_bool(source.get("PDFBOOK_READING_ORDER", "1")),
        style=source.get("PDFBOOK_STYLE", "fedele").strip() or "fedele",
    )


def _as_bool(raw: str | None) -> bool:
    return str(raw or "1").strip().lower() not in {"0", "false", "no", "off"}


def _as_float(raw: str | None, default: float) -> float:
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default
