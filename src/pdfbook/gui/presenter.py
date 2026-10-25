"""Logica di presentazione della GUI, senza Tk (Fase 6.1).

La GUI era "cieca": barra di avanzamento e log, nient'altro. Qui vive ciò che serve a
mostrare qualcosa di utile — stima del tempo rimasto, riepilogo della run, digest delle
issue per pagina, coppie originale/tradotto per l'anteprima — in funzioni pure, testabili
senza aprire una finestra.

Le regole sono volutamente semplici: una ETA che oscilla è peggio di nessuna ETA, quindi si
mostra solo dopo un campione minimo e si arrotonda al secondo.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field

from pdfbook.app.metrics import RunMetrics, format_metrics
from pdfbook.domain.models import PageLayout, QAReport

__all__ = [
    "MIN_SAMPLE_PAGES",
    "ProgressTracker",
    "ProgressView",
    "digest_lines",
    "issue_digest",
    "preview_pairs",
    "summary_lines",
]

#: Sotto questo numero di pagine la stima non è credibile e non si mostra.
MIN_SAMPLE_PAGES = 3


@dataclass
class ProgressTracker:
    """Trasforma i callback di avanzamento in percentuale e tempo rimasto."""

    started: float = 0.0
    current: int = 0
    total: int = 0
    rate_per_minute: float = 0.0
    _samples: list[tuple[float, int]] = field(default_factory=list)

    def begin(self, now: float, total: int) -> None:
        self.started = now
        self.current = 0
        self.total = max(total, 0)
        self._samples = [(now, 0)]

    def update(self, current: int, total: int, now: float) -> ProgressView:
        self.current = current
        self.total = max(total, 0)
        self._samples.append((now, current))
        elapsed = max(now - self.started, 0.0)
        if elapsed > 0:
            self.rate_per_minute = current / elapsed * 60.0
        remaining = max(self.total - current, 0)
        eta = (remaining / self.rate_per_minute * 60.0) if self.rate_per_minute > 0 else 0.0
        show_eta = current >= MIN_SAMPLE_PAGES and remaining > 0 and eta > 0
        return ProgressView(
            percent=(current / self.total) if self.total else 0.0,
            eta_seconds=int(round(eta)) if show_eta else None,
            pages_done=current,
            pages_total=self.total,
            rate_per_minute=self.rate_per_minute,
        )


@dataclass(frozen=True)
class ProgressView:
    percent: float
    eta_seconds: int | None
    pages_done: int
    pages_total: int
    rate_per_minute: float

    def label(self) -> str:
        base = f"{self.pages_done}/{self.pages_total} pagine"
        if self.rate_per_minute:
            base += f" · {self.rate_per_minute:.1f} pagine/min"
        if self.eta_seconds is not None:
            base += f" · mancano {_duration(self.eta_seconds)}"
        return base


def issue_digest(report: QAReport, *, limit: int = 20) -> dict[int, Counter]:
    """Issue raggruppate per pagina (le pagine con più problemi per prime)."""
    digest: dict[int, Counter] = {}
    for issue in report.issues:
        digest.setdefault(issue.page, Counter())[issue.kind.value] += 1
    ordered = sorted(digest.items(), key=lambda item: (-sum(item[1].values()), item[0]))
    return dict(ordered[: max(0, limit)])


def digest_lines(report: QAReport, *, limit: int = 8) -> list[str]:
    """Righe leggibili per l'ispettore: ``pagina 12 — clipped 3, font_reduced 2``."""
    lines: list[str] = []
    for page, counts in issue_digest(report, limit=limit).items():
        detail = ", ".join(f"{kind} {count}" for kind, count in counts.most_common())
        lines.append(f"pagina {page} — {detail}")
    return lines


def summary_lines(result, metrics: RunMetrics | None = None) -> list[str]:
    """Riepilogo di fine run: metriche, gate, glossario suggerito."""
    lines = [format_metrics(metrics)] if metrics else []
    if result.resumed_pages:
        lines.append(f"Ripresa: {result.resumed_pages} pagine dalla cache")
    violations = result.violations()
    lines.append("Gate: PASS" if not violations else "Gate: FAIL")
    lines.extend(f"GATE: {violation}" for violation in violations)
    for block_id, detail in _first_details(result.report, limit=3):
        lines.append(f"{block_id}: {detail}")
    if result.glossary_suggestions:
        lines.append("Glossario suggerito: " + ", ".join(result.glossary_suggestions[:8]))
    return lines


def preview_pairs(
    page: PageLayout, translations: Mapping[str, str], *, limit: int = 12
) -> list[tuple[str, str | None]]:
    """Coppie (originale, tradotto) nell'ordine di lettura della pagina, per l'anteprima."""
    pairs: list[tuple[str, str | None]] = []
    for block in page.blocks:
        original = block.text.strip()
        if not original:
            continue
        pairs.append((original, translations.get(block.id)))
        if len(pairs) >= limit:
            break
    return pairs


def _duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    minutes, rest = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {rest:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def _first_details(report: QAReport, *, limit: int) -> list[tuple[str, str]]:
    details: list[tuple[str, str]] = []
    for issue in report.issues:
        label = issue.block or f"pagina {issue.page}"
        details.append((label, issue.detail))
        if len(details) >= limit:
            break
    return details
