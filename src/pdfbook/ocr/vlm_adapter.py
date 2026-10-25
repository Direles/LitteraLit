"""OCR con VLM sidecar (Fase 4.3).

Per le scansioni difficili (due colonne, tabelle, calligrafia) un VLM addestrato al layout
legge la pagina e restituisce i blocchi con le coordinate, nel formato ``<|det|>``
(``ocr/det_parser.py``). Il modello gira tipicamente su un server locale compatibile OpenAI
(SGLang, vLLM, LM Studio): qui c'è il **client**, non il modello.

Il modulo non importa PyMuPDF: il PNG della pagina arriva da fuori (``render_png``), così la
politica di rendering resta nella sorgente e i test non aprono PDF.
"""

from __future__ import annotations

import base64
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pdfbook.domain.models import PageLayout

from .det_parser import parse_det, to_page_layout

__all__ = ["DEFAULT_PROMPT", "VlmConfig", "VlmOcr", "VlmOcrError"]

log = logging.getLogger(__name__)

DEFAULT_PROMPT = (
    "Transcribe this page. Emit one line per detected block in the format\n"
    "<|det|>type [x0, y0, x1, y1]text\n"
    "where type is one of: title, text, list, table, figure, caption, footnote, page_number. "
    "Coordinates are pixels of the image, origin top-left. Preserve the reading order."
)


class VlmOcrError(RuntimeError):
    """Il VLM non ha risposto o ha risposto male."""


@dataclass(frozen=True)
class VlmConfig:
    """Parametri del servizio VLM (compatibile OpenAI ``/chat/completions``)."""

    model: str
    base_url: str = "http://localhost:30000/v1"
    prompt: str = DEFAULT_PROMPT
    max_tokens: int = 4096
    temperature: float = 0.0
    timeout: float = 300.0
    api_key: str = ""

    @property
    def endpoint(self) -> str:
        return self.base_url.rstrip("/") + "/chat/completions"


@dataclass
class VlmOcr:
    """Trasforma il PNG di una pagina in ``PageLayout`` passando dal VLM."""

    config: VlmConfig
    post_json: Callable[[str, dict, dict], dict]
    render_png: Callable[[int], bytes]

    def page(self, index: int, *, number: int | None = None, width: float = 612.0, height: float = 792.0) -> PageLayout:
        """OCR di una pagina: ``index`` è 0-based, ``number`` è l'etichetta nel PDF."""
        raw = self._transcribe(self.render_png(index))
        parsed = parse_det(raw)
        if parsed.skipped:
            log.warning(
                "OCR pagina %s: %s blocchi scartati (%s)",
                number if number is not None else index + 1,
                parsed.skipped,
                parsed.problems[0] if parsed.problems else "formato inatteso",
            )
        if not parsed.blocks:
            raise VlmOcrError(
                "il modello non ha restituito blocchi <|det|>: controlla il prompt e il formato "
                "di risposta del server"
            )
        return to_page_layout(
            parsed.blocks,
            number=number if number is not None else index + 1,
            width=width,
            height=height,
        )

    def _transcribe(self, png: bytes) -> str:
        payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.config.prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": _data_url(png)},
                        },
                    ],
                }
            ],
        }
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        try:
            response = self.post_json(self.config.endpoint, payload, headers)
        except Exception as exc:  # noqa: BLE001 - trasporto eterogeneo: un solo errore pubblico
            raise VlmOcrError(f"VLM non raggiungibile su {self.config.endpoint}: {exc}") from exc
        return _first_message(response)


def _data_url(png: bytes) -> str:
    encoded = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _first_message(response: dict) -> str:
    """Testo del primo messaggio, con messaggi utili se il server risponde in altro modo."""
    choices: Sequence = response.get("choices") or []
    if not choices:
        raise VlmOcrError("risposta VLM senza 'choices'")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        raise VlmOcrError("risposta VLM senza testo")
    return content
