"""Registry dei provider: da configurazione a oggetto pronto all'uso (M2).

Unico punto che conosce endpoint e nomi commerciali: aggiungere un provider significa
una riga qui più un modulo in questa cartella (R9).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pdfbook.domain.models import TranslationSettings

from .anthropic import AnthropicProvider
from .base import DEFAULT_TIMEOUT, CompletionPort, ProviderError
from .gemini import GeminiProvider
from .openai_compatible import OpenAIChatProvider

__all__ = ["PROVIDER_NAMES", "create_provider", "provider_endpoint"]

_OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
_DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"

PROVIDER_NAMES: tuple[str, ...] = (
    "Google Gemini",
    "OpenAI",
    "DeepSeek",
    "Anthropic Claude",
    "Custom OpenAI-Compatible",
)

_ENDPOINTS = {
    "OpenAI": _OPENAI_ENDPOINT,
    "DeepSeek": _DEEPSEEK_ENDPOINT,
}

_REQUIRES_KEY = {"Google Gemini", "OpenAI", "DeepSeek", "Anthropic Claude"}

_NAME_SLUGS = {
    "Google Gemini": "gemini",
    "OpenAI": "openai",
    "DeepSeek": "deepseek",
    "Anthropic Claude": "anthropic",
    "Custom OpenAI-Compatible": "custom",
}


def provider_endpoint(settings: TranslationSettings) -> str:
    """Endpoint effettivo per la configurazione data (il custom usa ``base_url``)."""
    if settings.provider == "Custom OpenAI-Compatible":
        if not settings.base_url.strip():
            raise ProviderError("custom: 'base_url' obbligatoria")
        return settings.base_url.strip()
    return _ENDPOINTS.get(settings.provider, "")


def _openai_factory(
    name: str, settings: TranslationSettings, api_key: str, session: Any, timeout: float
) -> CompletionPort:
    return OpenAIChatProvider(
        name=_NAME_SLUGS[name],
        endpoint=provider_endpoint(settings),
        model=settings.model,
        api_key=api_key,
        session=session,
        timeout=timeout,
    )


_FACTORIES: dict[str, Callable[[str, TranslationSettings, str, Any, float], CompletionPort]] = {
    "OpenAI": _openai_factory,
    "DeepSeek": _openai_factory,
    "Custom OpenAI-Compatible": _openai_factory,
    "Google Gemini": lambda name, s, k, sess, t: GeminiProvider(
        model=s.model, api_key=k, session=sess, timeout=t, name=_NAME_SLUGS[name]
    ),
    "Anthropic Claude": lambda name, s, k, sess, t: AnthropicProvider(
        model=s.model, api_key=k, session=sess, timeout=t, name=_NAME_SLUGS[name]
    ),
}


def create_provider(
    settings: TranslationSettings,
    api_key: str,
    *,
    session: Any = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> CompletionPort:
    """Istanzia il provider descritto da ``settings`` (chiave obbligatoria salvo custom)."""
    name = settings.provider
    factory = _FACTORIES.get(name)
    if factory is None:
        raise ProviderError(f"provider sconosciuto: {name}")
    if name in _REQUIRES_KEY and not api_key.strip():
        raise ProviderError(f"{name}: chiave API obbligatoria")
    if name == "Custom OpenAI-Compatible":
        provider_endpoint(settings)  # valida 'base_url'
    return factory(name, settings, api_key, session, timeout)
