"""Provider Anthropic Claude (``/v1/messages``).

L'API non supporta il forcing di JSON: la riparazione avviene a valle (M1).
Con *extended thinking* attivo la risposta contiene prima un blocco ``thinking`` e poi
il blocco ``text``: si cerca sempre il primo blocco testuale, non il primo blocco.
"""

from __future__ import annotations

from typing import Any

from .base import DEFAULT_TIMEOUT, Completion, ProviderError, post_json

__all__ = ["AnthropicProvider"]

_ENDPOINT = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        session: Any = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_tokens: int = 4000,
        name: str = "anthropic",
    ) -> None:
        if not api_key:
            raise ProviderError("anthropic: chiave API obbligatoria")
        if not model:
            raise ProviderError("anthropic: modello obbligatorio")
        self.name = name
        self.model = model
        self.api_key = api_key
        self.session = session
        self.timeout = timeout
        self.max_tokens = max_tokens

    def complete(self, system: str, user: str) -> Completion:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        data = post_json(self.session, _ENDPOINT, self._headers(), payload, self.timeout)
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        return Completion(
            text=_text_block(data),
            tokens_in=_token(usage, "input_tokens"),
            tokens_out=_token(usage, "output_tokens"),
        )

    def _headers(self) -> dict[str, str]:
        return {
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": _API_VERSION,
        }


def _text_block(data: dict[str, Any]) -> str:
    blocks = data.get("content")
    if not isinstance(blocks, list) or not blocks:
        raise ProviderError("anthropic: risposta senza 'content'")
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                return text
    raise ProviderError("anthropic: nessun blocco di tipo 'text' nella risposta")


def _token(usage: dict[str, Any], key: str) -> int:
    try:
        return max(int(usage.get(key)), 0)
    except (TypeError, ValueError):
        return 0
