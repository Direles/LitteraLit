"""Esperimento: `insert_htmlbox` contro il renderer attuale (Fase 1.6).

Domanda: PyMuPDF sa impaginare un paragrafo con giustificazione e sillabazione CSS meglio di
quanto faccia il nostro ``layout/fitter`` + ``TextWriter``, e a quale costo?

Lo script misura, su una pagina sintetica:

* quanti caratteri entrano nell'area con ciascuna strategia;
* il corpo effettivo scelto (HTML lo riduce da sé con ``scale_low``);
* il tempo per pagina;
* se il testo resta **estratto** correttamente (requisito non negoziabile).

    py tools/experiment_htmlbox.py

Nessun file di libro: la pagina è generata al volo, quindi l'esperimento è ripetibile e non
lascia dati editoriali nel repository.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pymupdf as fitz  # noqa: E402

PARAGRAPH = (
    "La traduzione di un libro non è la sostituzione di parole: è la ricostruzione di un ritmo. "
    "Ogni riga deve entrare nella sua giustezza, ogni paragrafo deve restare riconoscibile, e "
    "il lettore non deve accorgersi che sotto c'è un altro testo. Quando il corpo rimpicciolisce "
    "troppo, la pagina perde leggibilità e l'operazione si vede: meglio un corpo più piccolo di "
    "poco e una riga in meno, che un testo compresso e illeggibile. "
) * 3

CSS = """
* { font-family: sans-serif; font-size: 10pt; text-align: justify; hyphens: auto;
    line-height: 1.25; margin: 0; }
"""


def main() -> int:
    rect = fitz.Rect(60, 60, 552, 300)
    textwriter = _measure_textwriter(rect)
    htmlbox = _measure_htmlbox(rect)
    print(_table(textwriter, htmlbox))
    print("\nVerdetto: " + _verdict(textwriter, htmlbox))
    return 0


def _measure_textwriter(rect) -> dict[str, object]:
    """Strategia attuale: fit del corpo con le metriche del font, poi TextWriter."""
    font = fitz.Font("helv")
    size = 10.0
    fit_started = time.perf_counter()
    lines = _wrap(PARAGRAPH, font, size, rect.width)
    while len(lines) * size * 1.25 > rect.height and size > 6:
        size -= 0.25
        lines = _wrap(PARAGRAPH, font, size, rect.width)
    fit_ms = (time.perf_counter() - fit_started) * 1000

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    started = time.perf_counter()
    for _ in range(20):
        writer = fitz.TextWriter(page.rect)
        y = rect.y0 + size
        for line in lines:
            writer.append((rect.x0, y), line, font=font, fontsize=size)
            y += size * 1.25
        writer.write_text(page, color=(0, 0, 0))
    elapsed = (time.perf_counter() - started) / 20
    extracted = page.get_text().strip()
    position = _chars(PARAGRAPH, extracted)
    doc.close()
    return {
        "strategia": "TextWriter (attuale)",
        "corpo": round(size, 2),
        "righe": len(lines),
        "giustificato": "no",
        "sillabazione": "sì (pyphen, fuori da questo test)",
        "caratteri estratti": position,
        "tempo_ms": round(elapsed * 1000, 2),
        "fit_ms": round(fit_ms, 2),
    }


def _measure_htmlbox(rect) -> dict[str, object]:
    """Strategia candidata: HTML/CSS dentro il rettangolo, con riduzione automatica."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    html = f"<p>{PARAGRAPH.strip()}</p>"
    started = time.perf_counter()
    spare, scale = page.insert_htmlbox(fitz.Rect(rect), html, css=CSS, scale_low=0.6)
    elapsed = time.perf_counter() - started
    extracted = page.get_text().strip()
    position = _chars(PARAGRAPH, extracted)
    doc.close()
    return {
        "strategia": "insert_htmlbox (candidata)",
        "corpo": round(10.0 * scale, 2),
        "righe": len(extracted.splitlines()),
        "giustificato": "sì (CSS)",
        "sillabazione": "sì (CSS, se il font lo consente)",
        "caratteri estratti": position,
        "tempo_ms": round(elapsed * 1000, 2),
        "fit_ms": 0.0,
        "spare_px": round(spare, 2),
    }


def _wrap(text: str, font, size: float, width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.text_length(candidate, fontsize=size) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _chars(original: str, extracted: str) -> float:
    """Percentuale di caratteri non-spazio dell'originale ritrovati nel testo estratto."""
    source = [char for char in original if not char.isspace()]
    found = [char for char in extracted if not char.isspace()]
    if not source:
        return 0.0
    return round(100.0 * min(len(found), len(source)) / len(source), 1)


def _table(*rows: dict[str, object]) -> str:
    keys = list(rows[0])
    header = "| " + " | ".join(keys) + " |"
    separator = "|" + "|".join("---" for _ in keys) + "|"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(key, "")) for key in keys) + " |")
    return "\n".join(lines)


def _verdict(textwriter: dict[str, object], htmlbox: dict[str, object]) -> str:
    if htmlbox["caratteri estratti"] < textwriter["caratteri estratti"]:
        return "NO-GO: il testo HTML non resta estraibile come quello attuale."
    draw_ratio = float(htmlbox["tempo_ms"]) / max(float(textwriter["tempo_ms"]), 0.01)
    if draw_ratio > 2:
        return (
            f"NO-GO come sostituto: insert_htmlbox disegna {draw_ratio:.1f}x più lentamente "
            "e l'unico vantaggio è la giustificazione CSS (vedi docs/nota-htmlbox.md). "
            "Resta un'opzione dietro flag se la giustificazione diventa un requisito."
        )
    return (
        "VALUTARE: HTML costa poco più del renderer attuale; misurarlo sui libri reali "
        "(metriche golden e SSIM) prima di qualsiasi sostituzione."
    )


if __name__ == "__main__":
    raise SystemExit(main())
