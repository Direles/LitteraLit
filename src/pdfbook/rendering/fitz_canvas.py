"""Adattatore PyMuPDF del canvas di pagina (M9).

Unico punto in cui il rendering tocca ``fitz``:

- la rimozione del testo usa ``apply_redactions(images=0, graphics=0, text=0)``: le
  immagini e la grafica restano intatte, i caratteri originali vengono eliminati;
- il disegno usa ``fitz.TextWriter`` con il font risolto (mai base-14 come ripiego:
  vedi §14.3b dell'architettura — il ripiego ``insert_text(..., 'helv')`` sostituiva
  em-dash e virgolette tipografiche);
- le righe che non possono essere disegnate vengono **restituite** al renderer, che le
  registra come ``TEXT_MISSING``.
"""

from __future__ import annotations

from collections.abc import Sequence

import pymupdf as fitz

from pdfbook.domain.models import Rect

from .canvas import TextRun

__all__ = ["FitzCanvas"]


class FitzCanvas:
    """Canvas concreto su una pagina PyMuPDF."""

    def __init__(self, page: fitz.Page) -> None:
        self.page = page
        self.width = float(page.rect.width)
        self.height = float(page.rect.height)
        self._pending_redactions = 0
        self.redactions_applied = 0

    def redact(self, box: Rect) -> None:
        self.page.add_redact_annot(fitz.Rect(box.normalized()))
        self._pending_redactions += 1

    def apply_redactions(self) -> None:
        if not self._pending_redactions:
            return
        self.page.apply_redactions(images=0, graphics=0, text=0)
        self.redactions_applied += self._pending_redactions
        self._pending_redactions = 0

    def draw(self, runs: Sequence[TextRun]) -> list[TextRun]:
        """Disegna raggruppando per colore (un ``TextWriter`` per colore)."""
        failures: list[TextRun] = []
        for color, group in _by_color(runs).items():
            writer = fitz.TextWriter(self.page.rect)
            drawn: list[TextRun] = []
            for run in group:
                try:
                    writer.append((run.x, run.baseline_y), run.text, font=run.font, fontsize=run.size)
                    drawn.append(run)
                except Exception:  # noqa: BLE001 - font o testo non disegnabile
                    failures.append(run)
            if not drawn:
                continue
            try:
                writer.write_text(self.page, color=color)
            except Exception:  # noqa: BLE001 - l'intero gruppo è perso
                failures.extend(drawn)
        return failures

    def text(self) -> str:
        """Testo estratto dalla pagina dopo il disegno (usato dal QA sui glifi)."""
        return self.page.get_text()


def _by_color(runs: Sequence[TextRun]) -> dict[tuple[float, float, float], list[TextRun]]:
    groups: dict[tuple[float, float, float], list[TextRun]] = {}
    for run in runs:
        key = tuple(round(channel, 4) for channel in run.color)
        groups.setdefault(key, []).append(run)
    return groups
