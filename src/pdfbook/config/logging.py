"""Logging strutturato su file, con rotazione (Fase 3.6).

Un job lungo senza log su disco è indiagnosticabile: se l'utente chiude la finestra, il
messaggio d'errore sparisce. Qui si configura un unico punto di logging che:

* scrive su **file con rotazione** (dimensione e numero di copie dichiarati);
* mantiene il console handler per la CLI e la GUI;
* non duplica handler se viene chiamato più volte (idempotente, testabile);
* non registra mai chiavi API: la redazione è già a monte (`settings.redacted`).

Il modulo non importa ``customtkinter`` né ``argparse``: lo usano CLI e GUI.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import tempfile
from pathlib import Path

__all__ = ["LOG_FORMAT", "configure", "default_log_path", "shutdown"]

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_HANDLER_MARK = "_pdfbook_handler"
MAX_BYTES = 2_000_000
BACKUPS = 3


def default_log_path(app: str = "pdfbook") -> Path:
    """Percorso scrivibile per il log, per sistema operativo."""
    override = os.environ.get("PDFBOOK_LOG_FILE", "").strip()
    if override:
        return Path(override)
    home = _home()
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = home / "Library" / "Logs"
    else:
        base = Path(os.environ.get("XDG_STATE_HOME") or home / ".local" / "state")
    return base / app / "pdfbook.log"


def _home() -> Path:
    """Home dell'utente, con ripiego sulla cartella temporanea (ambienti senza HOME)."""
    try:
        return Path.home()
    except RuntimeError:
        return Path(tempfile.gettempdir())


def configure(
    level: str = "INFO",
    *,
    log_file: str | os.PathLike[str] | None = None,
    console: bool = True,
    max_bytes: int = MAX_BYTES,
    backups: int = BACKUPS,
) -> Path | None:
    """Configura il logging di processo. Restituisce il file usato (o ``None``)."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_MARK, False):
            root.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(LOG_FORMAT)
    path: Path | None = None
    target = Path(log_file) if log_file else default_log_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            target, maxBytes=max(0, max_bytes), backupCount=max(0, backups), encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        setattr(file_handler, _HANDLER_MARK, True)
        root.addHandler(file_handler)
        path = target
    except OSError as exc:  # disco pieno, permessi: si continua con la console
        logging.getLogger(__name__).warning("log su file non attivato (%s): %s", target, exc)

    if console:
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        setattr(stream, _HANDLER_MARK, True)
        root.addHandler(stream)
    return path


def shutdown() -> None:
    """Chiude e stacca gli handler del progetto (usato dai test e a fine processo)."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_MARK, False):
            root.removeHandler(handler)
            handler.close()
