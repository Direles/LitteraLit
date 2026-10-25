"""Metriche di una run (Fase 7).

Un job che non lascia numeri non è osservabile: "ha funzionato" non dice quanto è costato,
quanto ha impiegato né dove si è perso tempo. Qui le metriche si calcolano da ciò che il job
già produce (``JobResult.summary`` e report), senza strumentazione sparsa nel codice.

Nessuna dipendenza, nessun ``print``: il modulo formatta stringhe che CLI, GUI e HTML usano.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field

__all__ = ["RunMetrics", "from_summary", "format_metrics"]


@dataclass(frozen=True)
class RunMetrics:
    """Fotografia di una run: volumi, tempi, costi, issue per tipo."""

    pages: int = 0
    blocks: int = 0
    seconds: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    issues: Mapping[str, int] = field(default_factory=dict)

    @property
    def pages_per_minute(self) -> float:
        return (self.pages / self.seconds * 60.0) if self.seconds > 0 else 0.0

    @property
    def blocks_per_page(self) -> float:
        return (self.blocks / self.pages) if self.pages else 0.0

    @property
    def cost_per_page(self) -> float:
        return (self.cost_usd / self.pages) if self.pages else 0.0

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total) if total else 0.0

    @property
    def blocking_issues(self) -> int:
        from pdfbook.qa.report import GATE_KINDS

        return sum(self.issues.get(kind.value, 0) for kind in GATE_KINDS)

    def as_dict(self) -> dict[str, float | int]:
        return {
            "pages": self.pages,
            "blocks": self.blocks,
            "seconds": round(self.seconds, 3),
            "pages_per_minute": round(self.pages_per_minute, 2),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": round(self.cost_usd, 4),
            "cost_per_page": round(self.cost_per_page, 4),
            "cache_hit_rate": round(self.cache_hit_rate, 3),
            "blocking_issues": self.blocking_issues,
        }


def from_summary(
    summary: Mapping[str, int],
    *,
    pages: int,
    blocks: int,
    seconds: float,
    issue_counts: Mapping[str, int] | Counter | None = None,
) -> RunMetrics:
    """Costruisce le metriche dai contatori del job (chiavi assenti = 0)."""
    counts = issue_counts or {}
    cost = summary.get("cost_usd_micro", 0)
    return RunMetrics(
        pages=pages,
        blocks=blocks,
        seconds=max(seconds, 0.0),
        tokens_in=int(summary.get("tokens_in", 0)),
        tokens_out=int(summary.get("tokens_out", 0)),
        cost_usd=(float(cost) / 1_000_000) if cost else float(summary.get("cost_usd", 0.0)),
        cache_hits=int(summary.get("cache_hits", 0)),
        cache_misses=int(summary.get("cache_misses", 0)),
        issues={kind: int(count) for kind, count in counts.items() if count},
    )


def format_metrics(metrics: RunMetrics) -> str:
    """Riga compatta per la CLI (una sola riga, niente tabelle)."""
    parts = [
        f"{metrics.pages} pagine in {metrics.seconds:.1f}s",
        f"{metrics.pages_per_minute:.1f} pagine/min",
        f"{metrics.blocks} blocchi",
    ]
    tokens = metrics.tokens_in + metrics.tokens_out
    if tokens:
        parts.append(f"{tokens} token")
    if metrics.cost_usd:
        parts.append(f"${metrics.cost_usd:.2f} (${metrics.cost_per_page:.3f}/pagina)")
    if metrics.cache_hits or metrics.cache_misses:
        parts.append(f"cache {metrics.cache_hit_rate:.0%}")
    if metrics.issues:
        top = ", ".join(
            f"{kind} {count}" for kind, count in sorted(metrics.issues.items(), key=lambda i: -i[1])[:4]
        )
        parts.append(f"issue: {top}")
    return " | ".join(parts)
