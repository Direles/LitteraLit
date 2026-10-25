"""Doppi di test condivisi: canvas, resolver, shortener e costruttori di dominio.

Evita la duplicazione di fixture fra i test di rendering e di pipeline (R7/R8) e tiene
i file di test sotto il budget di definizioni top-level.
"""

from __future__ import annotations

import json
from pathlib import Path

from pdfbook.app.runtime import Runtime
from pdfbook.domain.models import Line, PageLayout, Rect, Span, TextBlock
from pdfbook.translation.cache import TranslationCache
from pdfbook.translation.providers.base import ProviderError


class FakeCanvas:
    def __init__(self, fail_containing=None, snapshot_value=255):
        self.width = 612.0
        self.height = 792.0
        self.redactions = []
        self.applied = 0
        self.runs = []
        self.fail_containing = fail_containing
        self.snapshot_value = snapshot_value
        self.snapshots = 0

    def redact(self, box):
        self.redactions.append(box)

    def apply_redactions(self):
        self.applied += 1

    def draw(self, runs):
        self.runs.extend(runs)
        if not self.fail_containing:
            return []
        return [run for run in runs if self.fail_containing in run.text]

    def text(self):
        """Testo come lo vedrebbe l'estrattore: righe separate da spazio."""
        return " ".join(run.text for run in self.runs)

    def snapshot(self, dpi: float = 72.0):
        """Immagine uniforme: i test visivi usano canvas dedicati."""
        from pdfbook.qa.checks_visual import PageImage

        self.snapshots += 1
        size = 32
        return PageImage(
            pixels=bytes([self.snapshot_value]) * (size * size),
            width=size,
            height=size,
            pt_width=self.width,
        )


class FakeResolver:
    """Metrica finta: ogni carattere vale metà del corpo."""

    def __init__(self):
        self.resolved = []

    def resolve(self, pdf_font_name):
        self.resolved.append(pdf_font_name)
        return object()

    def text_length(self, text, pdf_font_name, fontsize):
        return len(text) * fontsize * 0.5


class FakeShortener:
    def __init__(self, result="Breve"):
        self.result = result
        self.calls = []

    def shorten(self, original, current, max_chars):
        self.calls.append((original, current, max_chars))
        return self.result


def make_line(text, *, x0=0.0, y0=100.0, width=200.0, size=10.0, color=0):
    return Line(
        spans=[Span(text=text, font_name="MinionPro-Regular", size=size, color=color)],
        bbox=Rect(x0, y0, x0 + width, y0 + size * 1.2),
        origin_y=y0 + size,
    )


def make_block(block_id, lines, *, bbox=None):
    lines = list(lines)
    if bbox is None:
        bbox = Rect(lines[0].bbox.x0, lines[0].bbox.y0, lines[-1].bbox.x1, lines[-1].bbox.y1)
    return TextBlock(id=block_id, bbox=bbox, lines=lines)


def make_page(*blocks, width=612.0, height=792.0, number=1):
    return PageLayout(number=number, width=width, height=height, blocks=list(blocks))


class FakeSource:
    """Sorgente di pagine già estratte; registra le pagine richieste."""

    def __init__(self, pages):
        self.pages = list(pages)
        self.requested: list[int] = []
        self.closed = False

    @property
    def page_count(self):
        return len(self.pages)

    def page(self, index):
        self.requested.append(index)
        return self.pages[index]

    def close(self):
        self.closed = True


class EchoProvider:
    """Provider deterministico: prefissa il testo invece di tradurlo."""

    name = "echo"

    def __init__(self, prefix="IT "):
        self.prefix = prefix
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        batch = json.loads(user)
        return json.dumps({key: self.prefix + value for key, value in batch.items()}, ensure_ascii=False)


class PartialProvider(EchoProvider):
    """Restituisce solo le prime ``keep`` chiavi: simula un blocco non tradotto."""

    def __init__(self, keep=1):
        super().__init__()
        self.keep = keep

    def complete(self, system, user):
        self.calls += 1
        batch = dict(list(json.loads(user).items())[: self.keep])
        return json.dumps(batch, ensure_ascii=False)


class FailingProvider:
    name = "failing"

    def __init__(self):
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        raise ProviderError("provider non disponibile")


class FixedProvider:
    """Restituisce sempre lo stesso testo (per simulare traduzioni inadatte)."""

    name = "fixed"

    def __init__(self, text="x"):
        self.text = text
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        return json.dumps({key: self.text for key in json.loads(user)}, ensure_ascii=False)


def make_runtime(source, provider, cache_path: Path, *, save_calls=None):
    """Runtime con dipendenze finte, per test della pipeline di documento."""
    return Runtime(
        source=source,
        provider=provider,
        cache=TranslationCache(cache_path, "part", autosave_every=0),
        resolver=FakeResolver(),
        canvas_factory=lambda index: FakeCanvas(),
        save=lambda path: (save_calls.append(path) if save_calls is not None else None),
        close=source.close,
        stats=lambda: {"embedded_fonts_reused": 0, "system_fonts_used": 1, "base14_fallback": 0},
    )
