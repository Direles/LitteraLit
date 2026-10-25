"""Provider Google Gemini (``generateContent``).

La chiave viaggia nell'header ``x-goog-api-key``, **non** in query string
(correzione del difetto §11.1/3: la chiave finiva in URL, log e proxy).
"""

from __future__ import annotations

from typing import Any

from .base import DEFAULT_TIMEOUT, Completion, ProviderError, post_json

__all__ = ["GeminiProvider"]

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        session: Any = None,
        timeout: float = DEFAULT_TIMEOUT,
        endpoint: str = _ENDPOINT,
        name: str = "gemini",
    ) -> None:
        if not api_key:
            raise ProviderError("gemini: chiave API obbligatoria")
        if not model:
            raise ProviderError("gemini: modello obbligatorio")
        self.name = name
        self.model = model
        self.api_key = api_key
        self.session = session
        self.timeout = timeout
        self.endpoint = endpoint.format(model=model)

    def complete(self, system: str, user: str) -> Completion:
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": f"{system}\n\n{user}"}]},
            ],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        data = post_json(self.session, self.endpoint, self._headers(), payload, self.timeout)
        metadata = data.get("usageMetadata") if isinstance(data.get("usageMetadata"), dict) else {}
        return Completion(
            text=_candidate_text(data),
            tokens_in=_token(metadata, "promptTokenCount"),
            tokens_out=_token(metadata, "candidatesTokenCount"),
        )

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json", "x-goog-api-key": self.api_key}


def _candidate_text(data: dict[str, Any]) -> str:
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        feedback = data.get("promptFeedback")
        if isinstance(feedback, dict):
            reason = feedback.get("blockReason", "motivo sconosciuto")
            raise ProviderError(f"gemini: richiesta bloccata ({reason})")
        raise ProviderError("gemini: risposta senza 'candidates'")
    candidate = candidates[0]
    content = candidate.get("content") if isinstance(candidate, dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list) or not parts:
        raise ProviderError("gemini: 'candidates[0].content.parts' assente")
    for part in parts:
        text = part.get("text") if isinstance(part, dict) else None
        if isinstance(text, str) and text.strip():
            return text
    raise ProviderError("gemini: nessuna parte testuale nella risposta")


def _token(metadata: dict[str, Any], key: str) -> int:
    try:
        return max(int(metadata.get(key)), 0)
    except (TypeError, ValueError):
        return 0
