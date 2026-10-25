"""Layer OCR (Fase 4): rende traducibili le scansioni.

Due strategie, in ordine di costo:

1. ``ocrmypdf`` + Tesseract — aggiunge uno strato di testo invisibile, la pipeline esistente
   funziona senza modifiche (Fase 4.2, implementata);
2. VLM sidecar (SGLang) — per scansioni difficili o layout complessi (Fase 4.3, prevista).

Il riconoscimento delle pagine scansionate vive in ``extraction/scan_detect.py``: qui c'è
solo il modo di *ripararle*.
"""

from __future__ import annotations

from .ocrmypdf_adapter import OcrConfig, OcrError, OcrSource, SubprocessRunner, ocrmypdf_command

__all__ = ["OcrConfig", "OcrError", "OcrSource", "SubprocessRunner", "ocrmypdf_command"]
