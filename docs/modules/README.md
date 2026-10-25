# Moduli — un file per contratto

Un file per modulo: responsabilità, interfaccia, invarianti, esempio d'uso, cosa **non** fa.
Massimo 200 righe. Se serve di più, il modulo è troppo grande (R1/R4).

Indice dei moduli esistenti: [`docs/MODULE_MAP.md`](../MODULE_MAP.md) §3.

| Documento | Modulo |
|---|---|
| [`domain.md`](domain.md) | `src/pdfbook/domain/models.py`, `src/pdfbook/domain/ports.py` |
| [`translation.md`](translation.md) | `src/pdfbook/translation/json_repair.py`, `src/pdfbook/translation/cache.py` |
| [`fonts.md`](fonts.md) | `src/pdfbook/fonts/resolver.py`, `src/pdfbook/fonts/platform_fonts.py`, `src/pdfbook/fonts/fitz_adapter.py` |
| [`layout.md`](layout.md) | `src/pdfbook/layout/`: `fitter.py`, `hyphenation.py`, `toc.py`, `segmentation.py`, `aligner.py` |
| [`rendering.md`](rendering.md) | `src/pdfbook/rendering/` (canvas, runs, painter, structured_painter, vector_renderer, fitz_canvas) |
| [`extraction.md`](extraction.md) | `src/pdfbook/extraction/pdf_extractor.py`, `src/pdfbook/extraction/fitz_source.py` |
| [`app.md`](app.md) | `src/pdfbook/app/`, `src/pdfbook/config/settings.py`, `src/pdfbook/cli.py`, `src/pdfbook/gui/` |