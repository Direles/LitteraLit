"""Report QA: costruzione, scrittura atomica e quality gate (M10).

Formato **compatibile** con i report prodotti finora dalla Gen 2 (``pages`` + ``summary``),
così gli strumenti esistenti continuano a leggerli, ma con due aggiunte:

- lettura tipizzata (``parse_report``) per usarli in CI;
- ``gate()``: elenco esplicito delle condizioni che rendono un output **non pubblicabile**.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from pdfbook.domain.models import IssueKind, QAIssue, QAReport

__all__ = [
    "REPORT_SUFFIX",
    "GATE_KINDS",
    "gate",
    "parse_report",
    "report_path",
    "write_report",
]

log = logging.getLogger(__name__)

REPORT_SUFFIX = "_qa_report.json"

# Issue che rendono l'output inaccettabile: testo perso, caratteri persi, non tradotto.
GATE_KINDS: tuple[IssueKind, ...] = (
    IssueKind.UNTRANSLATED_UNRESOLVED,
    IssueKind.GLYPH_MISSING,
    IssueKind.TEXT_MISSING,
    IssueKind.SPLIT_FAILED,
)


def report_path(pdf_path: str | os.PathLike[str]) -> Path:
    """Percorso del report accanto al PDF: ``libro.pdf`` → ``libro_qa_report.json``."""
    path = Path(pdf_path)
    stem = path.stem
    if stem.endswith("_qa_report"):
        return path
    return path.with_name(f"{stem}{REPORT_SUFFIX}")


def write_report(
    pdf_path: str | os.PathLike[str],
    report: QAReport,
    *,
    counters: Mapping[str, int] | None = None,
) -> Path:
    """Scrive il report accanto al PDF, in modo atomico (``*.tmp`` + ``os.replace``)."""
    target = report_path(pdf_path)
    payload = report.to_dict()
    if counters:
        payload["summary"] = {**counters, **payload["summary"]}
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, target)
    except OSError as exc:
        log.warning("report QA non salvato in %s: %s", target, exc)
        raise
    return target


def parse_report(data: Mapping[str, Any] | str | Path) -> QAReport:
    """Ricostruisce un ``QAReport`` da un report scritto (anche di formato storico)."""
    payload = _load(data)
    report = QAReport()
    for page_entry in payload.get("pages") or []:
        if not isinstance(page_entry, dict):
            continue
        page = int(page_entry.get("page", 0) or 0)
        for raw in page_entry.get("issues") or []:
            issue = _parse_issue(page, raw)
            if issue is not None:
                report.add(issue)
    for kind, value in (payload.get("summary") or {}).items():
        if kind in {item.value for item in IssueKind} and isinstance(value, int):
            report.counters[kind] = value
    return report


def gate(report: QAReport, *, kinds: Iterable[IssueKind] = GATE_KINDS) -> list[str]:
    """Violazioni del gate di pubblicazione: lista vuota = output accettabile."""
    violations: list[str] = []
    for kind in kinds:
        found = sum(1 for issue in report.issues if issue.kind == kind)
        if found:
            violations.append(f"{kind.value}: {found} occorrenze")
    return violations


def _load(data: Mapping[str, Any] | str | Path) -> Mapping[str, Any]:
    if isinstance(data, Mapping):
        return data
    path = Path(data)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("report QA illeggibile in %s: %s", path, exc)
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _parse_issue(page: int, raw: Any) -> QAIssue | None:
    if not isinstance(raw, dict):
        return None
    try:
        kind = IssueKind(str(raw.get("type", "")))
    except ValueError:
        return None
    block = raw.get("block")
    return QAIssue(
        page=int(raw.get("page", page) or page),
        kind=kind,
        block=str(block) if block is not None else None,
        detail=str(raw.get("detail", "")),
    )
