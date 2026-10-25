"""Esito di un job (Fase 3/6).

Estratto dalla pipeline per due motivi: il ``JobResult`` è il contratto verso CLI e GUI, e
tenerlo separato permette alla pipeline di restare sotto il budget dimensionale senza
sacrificare leggibilità.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pdfbook.domain.models import QAReport
from pdfbook.qa.report import gate

__all__ = ["JobResult"]


@dataclass
class JobResult:
    """Esito del job: file prodotti, report e conteggi."""

    output_pdf: Path
    report_path: Path
    report: QAReport
    pages: int = 0
    blocks: int = 0
    resumed_pages: int = 0
    summary: dict[str, int] = field(default_factory=dict)
    glossary_suggestions: list[str] = field(default_factory=list)

    def violations(self) -> list[str]:
        """Violazioni del gate di pubblicazione (vuoto = accettabile)."""
        return gate(self.report)
