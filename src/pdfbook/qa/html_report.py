"""Report QA in HTML, leggibile senza aprire il JSON (Fase 6.2).

Un report è per chi rilegge: pagina, tipo di problema, blocco, dettaglio. L'HTML è statico
(niente JS, niente CDN): CSS minimo incorporato, così il file si apre anche offline e si
può allegare a un preventivo o a una segnalazione.

Le issue bloccanti sono evidenziate; i conteggi arrivano dal ``summary`` del report.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from html import escape
from pathlib import Path
from typing import Any

from pdfbook.qa.report import parse_report

__all__ = ["HTML_SUFFIX", "html_from_report", "write_html"]

HTML_SUFFIX = "_qa_report.html"

_STYLE = """
body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; margin: 2rem auto;
       max-width: 60rem; color: #1d1d1f; background: #fbfbfd; }
h1 { font-size: 1.5rem; margin-bottom: .25rem; }
p.sub { color: #6e6e73; margin-top: 0; }
table { border-collapse: collapse; width: 100%; background: #fff;
        box-shadow: 0 1px 3px rgb(0 0 0 / 8%); border-radius: 8px; overflow: hidden; }
th, td { text-align: left; padding: .5rem .75rem; border-bottom: 1px solid #ececf1;
         font-size: .9rem; vertical-align: top; }
th { background: #f5f5f7; font-weight: 600; }
tr.blocking td { background: #fff3f3; }
code { background: #f5f5f7; padding: .1rem .3rem; border-radius: 4px; font-size: .85em; }
.counts { display: flex; gap: .5rem; flex-wrap: wrap; margin: 1rem 0; }
.count { background: #fff; border: 1px solid #ececf1; border-radius: 8px;
         padding: .35rem .6rem; font-size: .85rem; }
.count b { font-variant-numeric: tabular-nums; }
.empty { padding: 2rem; text-align: center; color: #6e6e73; }
"""

_BLOCKING = frozenset({"untranslated_unresolved", "glyph_missing", "text_missing", "split_failed"})


def html_from_report(data: Mapping[str, Any] | str | Path) -> str:
    """Costruisce l'HTML da un report QA (percorso o dizionario già letto)."""
    report = parse_report(data)
    issues = sorted(report.issues, key=lambda issue: (issue.page, issue.kind.value))
    counts = Counter(issue.kind.value for issue in issues)
    title = _title(data)
    parts = [
        "<!doctype html>",
        "<html lang=\"it\"><head><meta charset=\"utf-8\">",
        f"<title>Report QA — {escape(title)}</title>",
        f"<style>{_STYLE}</style></head><body>",
        f"<h1>Report QA — {escape(title)}</h1>",
        f"<p class=\"sub\">{len(issues)} issue su {_pages(issues)} pagine</p>",
        _counts_html(counts),
        _table(issues) if issues else "<p class=\"empty\">Nessuna issue registrata.</p>",
        "</body></html>",
    ]
    return "\n".join(parts)


def write_html(report_path: str | Path, output: str | Path | None = None) -> Path:
    """Scrive l'HTML accanto al report (o nel percorso indicato) e restituisce il percorso."""
    source = Path(report_path)
    target = Path(output) if output else source.with_name(source.stem + HTML_SUFFIX)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html_from_report(source), encoding="utf-8")
    return target


def _counts_html(counts: Counter[str]) -> str:
    if not counts:
        return ""
    chips = [
        f"<span class=\"count\">{escape(kind)} <b>{count}</b></span>"
        for kind, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    return "<div class=\"counts\">" + "".join(chips) + "</div>"


def _table(issues) -> str:
    rows = [
        "<table><thead><tr><th>Pagina</th><th>Tipo</th><th>Blocco</th><th>Dettaglio</th></tr></thead><tbody>"
    ]
    for issue in issues:
        css = " class=\"blocking\"" if issue.kind.value in _BLOCKING else ""
        block = f"<code>{escape(issue.block)}</code>" if issue.block else ""
        rows.append(
            f"<tr{css}><td>{issue.page}</td><td>{escape(issue.kind.value)}</td>"
            f"<td>{block}</td><td>{escape(issue.detail)}</td></tr>"
        )
    rows.append("</tbody></table>")
    return "".join(rows)


def _title(data: Mapping[str, Any] | str | Path) -> str:
    if isinstance(data, Mapping):
        return str(data.get("input") or data.get("output") or "documento")
    path = Path(data)
    return path.stem.replace("_qa_report", "")


def _pages(issues) -> int:
    return len({issue.page for issue in issues})
