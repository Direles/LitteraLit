# Modulo `domain` — strutture dati e contratti

**File**: `src/pdfbook/domain/models.py` (~250 righe), `src/pdfbook/domain/ports.py` (~100 righe)
**Layer**: `domain` — **non importa nulla** dal resto del package (R5).
**Test**: `tests/unit/test_domain_models.py`

## Responsabilità

1. Definire le strutture dati condivise da tutti i layer (nessun dizionario "selvaggio" di PyMuPDF che gira nel codice).
2. Definire i contratti (`Protocol`) con cui i layer comunicano senza dipendersi a vicenda.

Il modulo **non** estrae, **non** traduce, **non** disegna: non conosce PyMuPDF, le API LLM né i font.

## Interfaccia

### Dati (`models.py`)

| Tipo | Campi essenziali | Invarianti |
|---|---|---|
| `Rect` | `x0, y0, x1, y1` (punti PDF) | `x1 >= x0`, `y1 >= y0`; immutabile |
| `Span` | `text, font_name, size, color` | `color` è l'intero RGB di PyMuPDF |
| `Line` | `spans, bbox, origin_y` | almeno uno `Span` |
| `TextBlock` | `id, bbox, lines, kind` | almeno una `Line`; `id` unico **nella pagina** |
| `PageLayout` | `number, width, height, blocks, image_boxes` | `image_boxes` = ostacoli per il fitting |
| `TranslationSettings` | `provider, model, target_lang, base_url, glossary` | provider e model non vuoti |
| `QAIssue` / `QAReport` | `page, kind, block, detail` / `issues, counters` | `to_dict()` compatibile con i QA report storici |

Metodi con logica (tutti brevi, senza effetti collaterali):

| Metodo | Uso |
|---|---|
| `Rect.intersection`, `Rect.overlap_ratio`, `Rect.union` | QA geometrico (`text_overlap`), collisioni |
| `TextBlock.global_key(page)` | chiave stabile `p{page}:{block_id}` per la translation memory |
| `TranslationSettings.cache_partition()` | hash di provider+model+lingua+glossario → **partizione della cache** (corregge il difetto §11.2/2) |
| `TranslationSettings.with_glossary(terms)` | deduplica e ordina i termini, restituisce nuova istanza |
| `QAReport.add/count/issues_for_page/to_dict` | report QA in un unico punto |

### Contratti (`ports.py`)

| Protocol | Metodo | Implementato da |
|---|---|---|
| `DocumentSource` | `page_count`, `page(i)` | estrattore PDF, OCR, fixture |
| `TranslatorPort` | `translate(batch, context)` | `translation/providers/*` + pipeline |
| `ShortenerPort` | `shorten(original, current, max_chars)` | stessa pipeline (ritraduzione compressa) |
| `FontHandle` | `text_length`, `has_glyph` | wrapper di `fitz.Font` |
| `FontResolverPort` | `resolve(pdf_font_name)` | `fonts/resolver.py` |
| `ProgressPort` | `__call__(current, total, message)` | callback GUI/CLI |
| `RendererPort` | `render_page(page, translations)` | `rendering/vector_renderer.py` |
| `BlockClassifier` | `classify(block, page_area)` | `layout/segmentation.py` |

## Esempio d'uso

```python
from pdfbook.domain.models import QAReport, QAIssue, IssueKind, TranslationSettings

settings = TranslationSettings(provider="DeepSeek", model="deepseek-chat").with_glossary(["Sprint", "Backlog"])
report = QAReport()
report.add(QAIssue(page=3, kind=IssueKind.GLYPH_MISSING, detail="em-dash non reso"))
payload = report.to_dict()   # {"pages": [...], "summary": {...}}
key = settings.cache_partition()
```

## Cosa NON fa

- Non valida i dati di configurazione letti da file/env → `config/settings.py`.
- Non conosce il significato tipografico di `BlockKind` → lo decide `layout/segmentation.py`.
- Non serializza su disco → `qa/report.py` (scrittura), `translation/cache.py` (TM).
- Non contiene soglie o costanti di taratura (60% font, 0.75 ritraduzione, 1500 caratteri di contesto): quelle appartengono ai moduli che le usano, documentate in `docs/architecture/12-appendici.md` §16.

## Perché esiste (decisioni)

- **Rect immutabile**: gli shift verticali del renderer producono molte copie; l'immutabilità evita alias e bug "modifico il bbox di un blocco già processato".
- **`cache_partition()` nel dominio**: la chiave di cache è una proprietà della configurazione, non del provider; metterla qui impedisce che ogni adapter inventi la propria (era la causa del cache poisoning).
- **`QAReport` con enumerazione**: le issue diventano un contratto verificabile, non stringhe libere.
