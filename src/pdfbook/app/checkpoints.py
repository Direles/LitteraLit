"""Checkpoint di avanzamento: journal + salvataggio periodico della cache (Fase 3.1).

Il PDF viene ricostruito a ogni esecuzione (non è economico salvarlo incrementalmente), ma
la parte costosa — le chiamate al modello — vive nella translation memory. Qui si concentra:

- **fingerprint** del lavoro (input, impostazioni, intervallo): evita di riprendere un job
  con una configurazione diversa;
- **journal** con le pagine completate, scritto atomicamente;
- **salvataggio periodico della cache**, così un crash non brucia le traduzioni pagate.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from pdfbook.domain.models import TranslationSettings

from .errors import UsageError
from .journal import Journal, load_journal, save_journal

__all__ = ["checkpoint", "fingerprint", "start_journal"]

log = logging.getLogger(__name__)


def fingerprint(
    input_pdf: str | Path,
    settings: TranslationSettings,
    *,
    page_start: int | None,
    page_end: int | None,
    missing_policy: str,
    overflow_policy: str,
) -> str:
    """Identità stabile del lavoro in corso."""
    path = Path(input_pdf)
    try:
        info = path.stat()
        stat = f"{info.st_size}:{int(info.st_mtime)}"
    except OSError:
        stat = str(path)
    payload = "|".join([
        stat,
        settings.provider,
        settings.model,
        settings.target_lang,
        ",".join(settings.glossary),
        str(page_start),
        str(page_end),
        missing_policy,
        overflow_policy,
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def start_journal(
    *,
    input_pdf: str | Path,
    output_pdf: str | Path,
    fingerprint_value: str,
    pages_total: int,
    resume: bool,
) -> Journal:
    """Apre il journal esistente (se coerente) oppure ne crea uno nuovo."""
    existing = load_journal(output_pdf)
    if existing is not None and existing.fingerprint != fingerprint_value:
        if resume:
            raise UsageError(
                "il journal appartiene a un'altra configurazione "
                "(provider/modello/lingua/pagine): riesegui senza --resume"
            )
        log.warning("journal di una configurazione diversa: lo sovrascrivo")
        existing = None
    if existing is not None and resume:
        log.info(
            "ripresa: %s/%s pagine già tradotte (dalla cache)",
            existing.pages_done, pages_total,
        )
        return existing
    journal = Journal(
        input_pdf=str(input_pdf),
        output_pdf=str(output_pdf),
        fingerprint=fingerprint_value,
        pages_total=pages_total,
    )
    save_journal(journal)
    return journal


def checkpoint(journal: Journal, done: int, total: int, cache, every: int) -> None:
    """Salva cache e journal ogni ``every`` pagine (e sempre all'ultima)."""
    journal.pages_done = done
    journal.pages_total = total
    every = max(int(every), 1)
    if done % every and done != total:
        return
    cache.save()
    save_journal(journal)
