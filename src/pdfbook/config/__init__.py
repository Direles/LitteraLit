"""Configurazione: impostazioni applicative e ambiente.

Nessun segreto viene persistito (R11): la chiave vive solo in memoria o nell'ambiente.
"""

from .settings import (
    DEFAULT_CACHE_PATH,
    LANGUAGES,
    MODEL_SUGGESTIONS,
    AppSettings,
    load_env_file,
    load_settings,
    parse_glossary,
)

__all__ = [
    "DEFAULT_CACHE_PATH",
    "LANGUAGES",
    "MODEL_SUGGESTIONS",
    "AppSettings",
    "load_env_file",
    "load_settings",
    "parse_glossary",
]
