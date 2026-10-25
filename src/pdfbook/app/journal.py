"""Journal di avanzamento del job (Fase 3.1).

Il PDF viene ricostruito a ogni esecuzione (non è possibile salvarlo incrementalmente in
modo economico), ma la parte costosa — le chiamate al modello — è nella translation
memory. Il journal serve a due cose:

1. **salvare la cache periodicamente**, così un'interruzione non brucia le traduzioni già
   pagate;
2. dire all'utente (e a ``--resume``) a che pagina si era arrivati e con quale
   configurazione, evitando di riprendere un lavoro fatto con impostazioni diverse.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path

__all__ = ["JOURNAL_SUFFIX", "Journal", "journal_path", "load_journal", "remove_journal"]

log = logging.getLogger(__name__)

JOURNAL_SUFFIX = ".job.json"
_VERSION = 1


@dataclass
class Journal:
    """Stato minimo per riprendere senza sprechi."""

    input_pdf: str
    output_pdf: str
    fingerprint: str
    pages_total: int
    pages_done: int = 0
    version: int = _VERSION

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def progress(self) -> float:
        return 0.0 if not self.pages_total else self.pages_done / self.pages_total


def journal_path(output_pdf: str | os.PathLike[str]) -> Path:
    """Percorso del journal accanto al PDF di output."""
    return Path(output_pdf).with_name(Path(output_pdf).name + JOURNAL_SUFFIX)


def load_journal(output_pdf: str | os.PathLike[str]) -> Journal | None:
    """Legge il journal; ``None`` se assente, illeggibile o di versione sconosciuta."""
    path = journal_path(output_pdf)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("journal illeggibile (%s): lo ignoro", exc)
        return None
    if not isinstance(payload, dict) or payload.get("version") != _VERSION:
        log.warning("journal di versione non supportata: lo ignoro")
        return None
    try:
        return Journal(
            input_pdf=str(payload["input_pdf"]),
            output_pdf=str(payload["output_pdf"]),
            fingerprint=str(payload["fingerprint"]),
            pages_total=int(payload["pages_total"]),
            pages_done=int(payload.get("pages_done", 0)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("journal incompleto (%s): lo ignoro", exc)
        return None


def save_journal(journal: Journal) -> Path:
    """Scrittura atomica del journal."""
    path = journal_path(journal.output_pdf)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(journal.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)
    return path


def remove_journal(output_pdf: str | os.PathLike[str]) -> None:
    """Rimuove il journal (job completato)."""
    try:
        journal_path(output_pdf).unlink(missing_ok=True)
    except OSError as exc:  # pragma: no cover - filesystem esotico
        log.warning("journal non rimosso: %s", exc)
