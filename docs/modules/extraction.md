# Modulo `extraction` — da PDF a `PageLayout`

**File**: `extraction/pdf_extractor.py`, `extraction/fitz_source.py`
**Layer**: `extraction` — può importare solo `domain` (R5).
**Test**: `tests/unit/test_pdf_extractor.py` (16)
**Migrazione**: M8

## Responsabilità

| File | Responsabilità | Cosa NON fa |
|---|---|---|
| `pdf_extractor.py` | dizionario di `page.get_text('dict')` → `PageLayout` (blocchi, righe, span, ostacoli) | Non apre PDF, non classifica, non disegna |
| `fitz_source.py` | `PdfPageSource`: pagina *i* → `PageLayout` con le misure della pagina | Nessuna logica di conversione |

La separazione è deliberata: **la conversione non conosce PyMuPDF**, quindi si testa con
fixture JSON e si può riusare con un estrattore OCR (roadmap §14) che produce lo stesso
dizionario.

## Interfaccia

```python
extract_page(raw_page, *, number, width, height) -> PageLayout
block_from_raw(raw_block, index=0) -> TextBlock | None
line_from_raw(raw_line) -> Line | None
span_from_raw(raw_span) -> Span
image_box(raw_block) -> Rect | None
is_text_block(raw_block) -> bool

PdfPageSource.open(pdf_path) / .page_count / .page(i) -> PageLayout / .close()
```

## Regole di conversione

- blocchi non testuali → `image_boxes` (ostacoli per il fitting), **non** blocchi;
- righe vuote (anche solo spazi) → scartate; blocchi senza righe valide → scartati;
- `id` del blocco = `b{indice}` **progressivo dei blocchi validi**: i blocchi scartati non
  lasciano buchi nella numerazione (e quindi nelle chiavi di traduzione);
- `origin_y` dallo span se presente, altrimenti `bbox.y1 - size * 0.2`;
- bbox non valida (invertita o non numerica) → riga/blocco scartato, nessuna eccezione;
- le coordinate restano in **punti PDF**, come PyMuPDF.

## Verifica su libro reale

Sul PDF Patton, pagine 16 / 101 / 296: blocchi estratti **8/5/10**, identici ai blocchi
testuali del dizionario grezzo; caratteri 2.422 / 1.848 / 1.914 contro 2.390 / 1.823 /
1.888 (la differenza è il `\n` che separa le righe dentro il blocco).

## Pagine scansionate (Fase 4.1)

```python
has_text(page) -> bool                   # ≥ 20 caratteri non di spazi
is_scanned_page(page) -> bool            # nessun testo utile ma almeno un'immagine
scan_report(pages) -> ScanReport         # pages, with_text, scanned, all_scanned/mostly_scanned
ScanReport.message() -> str              # messaggio azionabile per l'utente
```

Una pagina senza testo e con un'immagine è una scansione: `page_render` registra
`scan_page` e il job, se non ha tradotto nulla, chiude con un errore che dice di fare un OCR
preliminare (`ocrmypdf`). Il modulo **non fa OCR**: classifica soltanto, così l'adapter della
Fase 4.2 sa su quali pagine intervenire.

## OCR (Fase 4.2)

```python
OcrConfig(language="ita+eng", jobs=0, deskew=True, rotate_pages=True, skip_text=True)
ocrmypdf_command(input, output, config) -> list[str]
OcrSource.open(pdf, *, config=None, runner=None, opener=PdfPageSource.open)
looks_scanned(source, sample=6) -> bool
```

`OcrSource.open` è trasparente: se il PDF ha già testo restituisce la sorgente originale senza
eseguire nulla. Se è una scansione (maggioranza delle pagine campionate senza testo):

1. crea una **copia temporanea** in `%TEMP%/pdfbook-ocr-*`;
2. esegue `ocrmypdf --skip-text --deskew --rotate-pages` (strato di testo invisibile);
3. apre la copia e la usa come sorgente; `close()` cancella la cartella.

Errori tradotti in `OcrError` con l'istruzione di installazione (Tesseract incluso), timeout a
un'ora, e nessun effetto sul PDF originale. Con `PDFBOOK_OCR=off` il passo è disattivato.

## Cosa NON fa e dove andrà

- **Classificazione** (prosa, titolo, indice, colonna) → `layout/segmentation.py`.
- **Font** (quale font usare, copertura glifi) → `fonts/resolver.py`.
- **OCR** per PDF scansionati → `ocr/` (Fase 4.2: `ocrmypdf`; Fase 4.3: VLM sidecar).

## Note per chi modifica

1. Se il dizionario di PyMuPDF cambia forma, si aggiorna solo questo modulo e le fixture.
2. Non introdurre `import fitz` qui: romperebbe la testabilità e la regola R5 della
   separazione fra conversione e trasporto.
3. Ogni campo nuovo di `PageLayout` va aggiunto in `domain/models.py` con un test.
