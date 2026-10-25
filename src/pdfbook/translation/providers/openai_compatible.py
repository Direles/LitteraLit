"""Provider per API OpenAI-compatibili: OpenAI, DeepSeek, endpoint custom.

Una sola implementazione perché il protocollo è identico; cambiano solo endpoint e
credenziali, che arrivano dal registry (``translation/providers/registry.py``).
"""

from __future__ import annotations

from typing import Any

from .base import DEFAULT_TIMEOUT, ProviderError, post_json

__all__ = ["OpenAIChatProvider"]

_CHAT_SUFFIX = "/chat/completions"


class OpenAIChatProvider:
    """Chat completions con ``response_format=json_object``."""

    def __init__(
        self,
        *,
        name: str,
        endpoint: str,
        model: str,
        api_key: str,
        session: Any = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        if not model:
            raise ProviderError(f"{name}: modello obbligatorio")
        if not endpoint:
            raise ProviderError(f"{name}: endpoint obbligatorio")
        self.name = name
        self.endpoint = endpoint if endpoint.endswith(_CHAT_SUFFIX) else endpoint.rstrip("/") + _CHAT_SUFFIX
        self.model = model
        self.api_key = api_key
        self.session = session
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        data = post_json(self.session, self.endpoint, self._headers(), payload, self.timeout)
        return _message_content(self.name, data)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def _message_content(name: str, data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderError(f"{name}: risposta senza 'choices'")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise ProviderError(f"{name}: 'message.content' assente o vuoto")
    return content
