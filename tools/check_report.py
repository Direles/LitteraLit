"""Modello e stampa del report per ``modularity_check`` (separato per rispettare R1).

Contiene solo: una issue, un contenitore con conteggi e la formattazione finale.
Nessuna regola: quelle vivono in ``modularity_check.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["Issue", "Report", "exit_code", "render"]


@dataclass
class Issue:
    level: str
    rule: str
    where: str
    line: int
    message: str


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)
    scanned: int = 0

    def add(self, level: str, rule: str, where: str, line: int, message: str) -> None:
        self.issues.append(Issue(level, rule, where, line, message))

    def count(self, level: str) -> int:
        return sum(1 for issue in self.issues if issue.level == level)

    def by_rule(self) -> dict[str, list[Issue]]:
        grouped: dict[str, list[Issue]] = {}
        for issue in self.issues:
            grouped.setdefault(f"{issue.level}/{issue.rule}", []).append(issue)
        return grouped


def render(report: Report) -> None:
    """Stampa il report: massimo 5 esempi per regola, conteggi completi."""
    print(
        f"== modularity_check == file analizzati: {report.scanned} | "
        f"errori: {report.count('ERROR')} | warning: {report.count('WARN')}"
    )
    for key in sorted(report.by_rule(), key=lambda k: (not k.startswith("ERROR"), k)):
        issues = report.by_rule()[key]
        print(f"\n-- {key}: {len(issues)}")
        for issue in issues[:5]:
            print(f"   {issue.where}:{issue.line}  {issue.message}")
        if len(issues) > 5:
            print(f"   ... e altri {len(issues) - 5}")
    if not report.issues:
        print("\nNessuna violazione: struttura conforme ad AGENTS.md.")


def exit_code(report: Report, *, strict: bool) -> int:
    """1 se ci sono errori (o warning in modalità strict), altrimenti 0."""
    failed = report.count("ERROR") > 0 or (strict and report.count("WARN") > 0)
    return 1 if failed else 0
