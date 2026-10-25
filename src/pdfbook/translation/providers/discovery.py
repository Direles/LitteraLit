"""Scoperta dei modelli su un endpoint locale (Fase 6.1/7).

LM Studio, Ollama, vLLM e llama.cpp espongono tutti ``GET /v1/models`` in formato OpenAI.
Leggere quell'elenco evita il primo errore di ogni configurazione locale: scrivere un nome
di modello che non esiste (o che non è caricato).

Il modulo non apre connessioni nei test: il trasporto è iniettabile (``get_json``).
Nessuna chiave viene loggata; per gli endpoint locali la chiave è di norma vuota.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import requests

from .base import ProviderError

__all__ = [
    "LOCAL_PRESETS",
    "ModelInfo",
    "is_local",
    "list_models",
    "models_endpoint",
    "parse_models",
]

log = logging.getLogger(__name__)

#: Endpoint tipici dei server locali compatibili OpenAI.
LOCAL_PRESETS: dict[str, str] = {
    "lm-studio": "http://localhost:1234/v1",
    "ollama": "http://localhost:11434/v1",
    "vllm": "http://localhost:8000/v1",
    "llama.cpp": "http://localhost:8080/v1",
}

_LOCAL_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal")


@dataclass(frozen=True)
class ModelInfo:
    """Un modello disponibile sull'endpoint."""

    id: str
    owned_by: str = ""
    context_length: int = 0

    @property
    def label(self) -> str:
        extra = f" ({self.context_length} token)" if self.context_length else ""
        return f"{self.id}{extra}"


def is_local(base_url: str) -> bool:
    """``True`` se l'URL punta a una macchina locale (nessuna chiave necessaria)."""
    lowered = (base_url or "").lower()
    return any(host in lowered for host in _LOCAL_HOSTS)


def models_endpoint(base_url: str) -> str:
    """``http://localhost:1234`` → ``http://localhost:1234/v1/models``."""
    base = (base_url or "").strip().rstrip("/")
    if not base:
        raise ProviderError("base_url vuota: indica l'endpoint del server locale")
    if not base.startswith(("http://", "https://")):
        base = "http://" + base
    if not base.endswith("/v1"):
        base = base + "/v1"
    return base + "/models"


def parse_models(payload: Mapping[str, Any]) -> list[ModelInfo]:
    """Estrae i modelli dalla risposta OpenAI (``data``) o Ollama (``models``)."""
    entries = payload.get("data") or payload.get("models") or []
    models: list[ModelInfo] = []
    seen: set[str] = set()
    if not isinstance(entries, list):
        return models
    for entry in entries:
        if isinstance(entry, str):
            identifier, owned, context = entry, "", 0
        elif isinstance(entry, Mapping):
            identifier = str(entry.get("id") or entry.get("name") or entry.get("model") or "")
            owned = str(entry.get("owned_by") or entry.get("publisher") or "")
            context = _context_length(entry)
        else:
            continue
        identifier = identifier.strip()
        if not identifier or identifier in seen:
            continue
        seen.add(identifier)
        models.append(ModelInfo(identifier, owned, context))
    return models


def list_models(
    base_url: str,
    *,
    api_key: str = "",
    timeout: float = 5.0,
    get_json: Callable[[str, dict[str, str], float], Mapping[str, Any]] | None = None,
) -> list[ModelInfo]:
    """Modelli caricati sull'endpoint; ``ProviderError`` se il server non risponde."""
    url = models_endpoint(base_url)
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    fetcher = get_json or _get_json
    try:
        payload = fetcher(url, headers, timeout)
    except ProviderError:
        raise
    except requests.RequestException as exc:
        log.debug("lettura modelli fallita su %s: %s", base_url, exc)
        raise ProviderError(
            f"nessun server su {base_url}. In LM Studio: scheda Server → Start Server; "
            "oppure controlla PDFBOOK_BASE_URL."
        ) from exc
    models = parse_models(payload)
    log.debug("modelli disponibili su %s: %s", url, [model.id for model in models])
    return models


def _get_json(url: str, headers: dict[str, str], timeout: float) -> Mapping[str, Any]:
    response = requests.get(url, headers=headers, timeout=timeout)
    if response.status_code >= 400:
        raise ProviderError(f"{url} ha risposto {response.status_code}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise ProviderError(f"risposta non JSON da {url}") from exc
    if not isinstance(payload, Mapping):
        raise ProviderError(f"formato inatteso da {url}")
    return payload


def _context_length(entry: Mapping[str, Any]) -> int:
    for key in ("context_length", "max_context_length", "context_window", "n_ctx"):
        value = entry.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return int(value)
    return 0
