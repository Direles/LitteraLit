"""Trasporto HTTP e contratti comuni ai provider (M2).

Un solo punto per: timeout, estrazione del messaggio d'errore, validazione della risposta.
Nessun retry (è responsabilità della pipeline, M4) e nessuna conoscenza del formato JSON
del modello (è responsabilità di ``translation/json_repair.py``, M1).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

import requests

__all__ = [
    "DEFAULT_TIMEOUT",
    "CompletionPort",
    "ProviderError",
    "error_detail",
    "post_json",
]

DEFAULT_TIMEOUT = 60.0
_ERROR_SNIPPET = 300


class ProviderError(RuntimeError):
    """Errore di trasporto o di forma della risposta del provider."""


@runtime_checkable
class CompletionPort(Protocol):
    """Contratto minimo di un provider: da due prompt a un testo."""

    name: str

    def complete(self, system: str, user: str) -> str: ...


@runtime_checkable
class HttpSession(Protocol):
    """Sottoinsieme di ``requests.Session`` usato dai provider (iniettabile nei test)."""

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any],
        timeout: float,
    ) -> Any: ...


def error_detail(response: Any) -> str:
    """Messaggio d'errore del provider, troncato: mai l'intero payload."""
    status = getattr(response, "status_code", "?")
    try:
        data = response.json()
    except Exception:  # noqa: BLE001 - qualunque corpo non JSON va degradato
        text = (getattr(response, "text", "") or "").strip()
        return text[:_ERROR_SNIPPET] or f"HTTP {status}"
    for key in ("message", "detail"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, str):
            return value[:_ERROR_SNIPPET]
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, str):
        return error[:_ERROR_SNIPPET]
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"][:_ERROR_SNIPPET]
    return f"HTTP {status}"


def post_json(
    session: Any,
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any],
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """POST JSON con errori normalizzati in ``ProviderError``."""
    poster = session.post if session is not None else requests.post
    try:
        response = poster(url, headers=headers, json=dict(payload), timeout=timeout)
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise ProviderError(f"HTTP {getattr(response, 'status_code', '?')}: {error_detail(response)}") from exc
    except requests.RequestException as exc:
        raise ProviderError(f"errore di rete ({type(exc).__name__})") from exc
    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderError("la risposta non è JSON") from exc
    if not isinstance(data, dict):
        raise ProviderError("la risposta JSON non è un oggetto")
    return data
