"""Provider LLM: un modulo per protocollo, un registry per la scelta (M2).

Import di comodo: ``from pdfbook.translation.providers import create_provider``.
"""

from .base import (
    DEFAULT_TIMEOUT,
    Completion,
    CompletionPort,
    ProviderError,
    error_detail,
    post_json,
)
from .registry import PROVIDER_NAMES, create_provider, provider_endpoint

__all__ = [
    "DEFAULT_TIMEOUT",
    "PROVIDER_NAMES",
    "Completion",
    "CompletionPort",
    "ProviderError",
    "create_provider",
    "error_detail",
    "post_json",
    "provider_endpoint",
]
