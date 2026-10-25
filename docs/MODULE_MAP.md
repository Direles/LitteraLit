# MODULE_MAP — indice di routing e registro dei moduli

> **Leggi solo questo file per capire dove intervenire.**
> Se una voce manca: non esplorare il repository — aggiungi la voce (R10) o proponi un nuovo modulo (R9).
> Documento gemello: [`AGENTS.md`](../AGENTS.md) (regole). Overview architetturale: [`docs/architecture/README.md`](architecture/README.md).

---

## 1. Routing rapido — "se devi… → apri…"

La colonna *Provenienza* indica da quale file della Gen 2 è stato migrato il modulo: quei file
sono stati rimossi dopo M11 e **non vanno cercati nel repository**.

| Se devi… | Apri (target) | Provenienza (app Gen 2) | NON toccare |
|---|---|---|---|
| Cambiare le istruzioni/prompt di traduzione | `translation/prompts.py` | `conversione gemini/translator.py` → `translate_batch` | renderer, fonts |
| Aggiungere o correggere un provider LLM | `translation/providers/<nome>.py` + `translation/providers/registry.py` | `translator._call_llm` | pipeline, cache |
| Correggere il parsing delle risposte | `translation/json_repair.py` | `translator.robust_json_parse`, `escape_unescaped_quotes` | provider |
| Cambiare la cache / la chiave di cache | `translation/cache.py` | `translator.load_cache/save_cache/get_cache_key` | renderer |
| Ritraduzione compressa / batching / retry | `translation/pipeline.py` | `translator.translate_batch`, `translate_shorter` | layout |
| Scegliere il font da usare (embedded/sistema) | `fonts/resolver.py` | `conversione gemini/fonts.py` | rendering |
| Aggiungere un font di fallback per OS | `fonts/platform_fonts.py` | `fonts.SYSTEM_FAMILIES`, `WIN_FONTS` | resolver |
| Correggere a capo / corpo / fit del testo | `layout/fitter.py` | `rebuild_vector.fit_font`, `wrap_text` | estrazione |
| Righe d'indice (dot-leader) | `layout/toc.py` | `rebuild_vector.optimize_toc_line`, `_is_toc_line` | fitter |
| Sillabazione | `layout/hyphenation.py` | `rebuild_vector._hyphenate_word`, `PYPHEN_LANGS` | fitter |
| Allineamento (left/center/right) | `layout/aligner.py` | `rebuild_vector.detect_*_alignment` | rendering |
| Riconoscere indici, colonne, blocchi strutturati | `layout/segmentation.py` | `rebuild_vector._group_rows`, `_is_toc_line`, `optimize_toc_line` | fitter |
| Estrarre blocchi/righe/spans dal PDF | `extraction/pdf_extractor.py` | `rebuild_vector.process_pdf_vector` (parte iniziale) | rendering |
| Redigere e inserire il testo tradotto | `rendering/vector_renderer.py` | `rebuild_vector.process_pdf_vector` (parte finale) | estrazione |
| Report QA / nuove issue | `qa/report.py` | `rebuild_vector` (contatori + dump) | renderer |
| GUI, thread, progress, log | `gui/app.py` | `conversione gemini/app_gui.py` | dominio |
| Config, chiavi, glossario | `config/settings.py` | `app_gui.load_config/save_config`, `config.json` | codice |
| OCR/VLM (sidecar) | `ocr/client.py` | — (da creare, vedi arch. §14) | pipeline testo |
| Strutture dati condivise (blocchi, rect, settings) | `domain/models.py` | sparse nei dict PyMuPDF | — |
| Contratti tra moduli (Protocol) | `domain/ports.py` | assenti (monkeypatch nei test) | — |

Se la risposta alla tua domanda richiede più di 2 righe di questa tabella, il modulo è mal separato: R4.

---

## 2. Struttura target

```
src/pdfbook/
├── domain/          models.py, ports.py                  ← nessuna dipendenza interna
├── config/          settings.py                          ← segreti via env/keyring
├── extraction/      pdf_extractor.py
├── layout/          segmentation.py, fitter.py, hyphenation.py, aligner.py
├── fonts/           resolver.py, platform_fonts.py
├── translation/     pipeline.py, prompts.py, cache.py, json_repair.py
│   └── providers/   registry.py, gemini.py, openai.py, deepseek.py, anthropic.py, custom.py
├── rendering/       canvas.py, runs.py, painter.py, structured_painter.py, vector_renderer.py, fitz_canvas.py
├── qa/              report.py, checks_geometry.py, checks_glyphs.py
├── ocr/             client.py (opzionale, sidecar)
├── app/             pipeline.py, runtime.py
├── gui/             app.py, config_panel.py, widgets/*.py
└── cli.py
tools/               modularity_check.py
tests/unit/          test_<modulo>.py
docs/architecture/   overview a sezioni
docs/modules/        un file per modulo
legacy/              codice Gen 1 congelato
```

---

## 3. Registro moduli

| Path | Layer | Responsabilità (una riga) | Budget | Stato | Test |
|---|---|---|---|---|---|
| `src/pdfbook/domain/models.py` | domain | Dataclass condivise: `Rect`, `Span`, `Line`, `TextBlock`, `PageLayout`, `TranslationSettings`, `QAIssue`, `QAReport` | 220 | **esistente** | `tests/unit/test_domain_models.py` |
| `src/pdfbook/domain/ports.py` | domain | Protocol: `TranslatorPort`, `ShortenerPort`, `FontResolverPort`, `ProgressPort`, `DocumentSource` | 120 | **esistente** | — (solo tipi) |
| `src/pdfbook/config/settings.py` | config | Impostazioni da env/`.env`, validazione, nessun segreto su disco | 200 | **esistente (M11)** | `tests/unit/test_settings.py` |
| `src/pdfbook/config/pricing.py` | config | Tabella prezzi indicativi e stima del costo di una run | 70 | **esistente (Fase 3.3)** | `tests/unit/test_pricing_ratelimit.py` |
| `src/pdfbook/config/logging.py` | config | Log su file con rotazione, idempotente, senza segreti | 90 | **esistente (Fase 3.6)** | `tests/unit/test_logging_setup.py` |
| `src/pdfbook/app/runtime.py` | app | Costruzione dipendenze reali (PDF, provider, cache, font, canvas) | 110 | **esistente (M11)** | `tests/unit/test_app_pipeline.py` |
| `src/pdfbook/app/pipeline.py` | app | Job di documento: pagine → batch → render → QA → salvataggio | 330 | **esistente (M11/Fase 3)** | `tests/unit/test_app_pipeline.py` |
| `src/pdfbook/app/page_translator.py` | app | Traduzione della pagina: unità, split delle continuazioni, glossario | 110 | **esistente (Fase 2/5)** | `tests/unit/test_app_pipeline.py` |
| `src/pdfbook/app/page_render.py` | app | Rendering di pagina + QA visivo/glifi e contatori | 60 | **esistente (Fase 0/3)** | `tests/integration/test_pipeline_fixtures.py` |
| `src/pdfbook/app/visual_qa.py` | app | Fotografia prima/dopo e confronto visivo di pagina | 60 | **esistente (Fase 0)** | `tests/unit/test_checks_visual.py` |
| `src/pdfbook/app/costs.py` | app | Contabilità token/costo e tetto di spesa | 60 | **esistente (Fase 3.3)** | `tests/unit/test_app_pipeline.py` |
| `src/pdfbook/app/metrics.py` | app | Metriche di run: pagine/min, token, costo/pagina, cache hit, issue | 110 | **esistente (Fase 7)** | `tests/unit/test_metrics.py` |
| `src/pdfbook/app/job_result.py` | app | Contratto di uscita del job (file, report, conteggi, violazioni) | 45 | **esistente (Fase 6.1)** | `tests/unit/test_app_pipeline.py` |
| `src/pdfbook/app/checkpoints.py` | app | Fingerprint del lavoro, journal di avanzamento, salvataggio periodico della cache | 110 | **esistente (Fase 3.1)** | `tests/unit/test_journal.py` |
| `src/pdfbook/app/journal.py` | app | Modello e I/O atomico del journal | 110 | **esistente (Fase 3.1)** | `tests/unit/test_journal.py` |
| `src/pdfbook/app/errors.py` | app | Classificazione errori, codici di uscita e messaggi azionabili | 90 | **esistente (Fase 3.4)** | `tests/unit/test_errors.py` |
| `src/pdfbook/extraction/pdf_extractor.py` | extraction | PDF dict → `PageLayout` (blocchi, righe, span, ostacoli) | 190 | **esistente (M8)** | `tests/unit/test_pdf_extractor.py` |
| `src/pdfbook/extraction/fitz_source.py` | extraction | Unico punto con `fitz`: `PdfPageSource.page(i)` | 60 | **esistente (M8)** | smoke test |
| `src/pdfbook/extraction/scan_detect.py` | extraction | Pagine senza testo con immagini = scansioni, messaggio azionabile | 110 | **esistente (Fase 4.1)** | `tests/unit/test_scan_detect.py` |
| `src/pdfbook/ocr/ocrmypdf_adapter.py` | ocr | OCR via ocrmypdf su copia temporanea, solo se la pagina è scansionata | 180 | **esistente (Fase 4.2)** | `tests/unit/test_ocrmypdf_adapter.py` |
| `src/pdfbook/ocr/det_parser.py` | ocr | Parser del formato `<\|det\|>tipo [bbox]testo` dei VLM | 150 | **esistente (Fase 4.3)** | `tests/unit/test_vlm_ocr.py` |
| `src/pdfbook/ocr/vlm_adapter.py` | ocr | Client VLM compatibile OpenAI: PNG → blocchi tipografici | 150 | **esistente (Fase 4.3)** | `tests/unit/test_vlm_ocr.py` |
| `src/pdfbook/layout/segmentation.py` | layout | Righe visive, indici, classificazione blocchi | 150 | **esistente (M7)** | `tests/unit/test_segmentation.py` |
| `src/pdfbook/layout/fitter.py` | layout | `wrap_text`, `fit_text`, budget caratteri; metriche iniettate | 200 | **esistente (M6)** | `tests/unit/test_fitter.py` |
| `src/pdfbook/layout/hyphenation.py` | layout | Sillabazione per lingua (pyphen, degrado dichiarato) | 90 | **esistente (M6)** | `tests/unit/test_hyphenation.py` |
| `src/pdfbook/layout/toc.py` | layout | Riconoscimento e riallineamento delle righe d'indice | 70 | **esistente (M6)** | `tests/unit/test_toc.py` |
| `src/pdfbook/layout/flow.py` | layout | Paragraph stitching fra pagine + ridistribuzione della traduzione | 200 | **esistente (Fase 2)** | `tests/unit/test_flow.py` |
| `src/pdfbook/layout/scripts.py` | layout | Riconoscimento apici/pedici da corpo e baseline, scala e spostamento | 90 | **esistente (Fase 1.3)** | `tests/unit/test_styles.py` |
| `src/pdfbook/layout/columns.py` | layout | Ordine di lettura a due colonne con gutter netto, fallback prudente | 150 | **esistente (Fase 2.5)** | `tests/unit/test_columns.py` |
| `src/pdfbook/layout/notes.py` | layout | Note a piè di pagina: corpo piccolo + fascia bassa + marcatore | 120 | **esistente (Fase 2.6)** | `tests/unit/test_notes.py` |
| `src/pdfbook/layout/writing_system.py` | layout | Sistema di scrittura dominante e blocchi non ancora supportati (RTL/CJK) | 110 | **esistente (Fase 4.5, parziale)** | `tests/unit/test_writing_system.py` |
| `src/pdfbook/layout/page_furniture.py` | layout | Header, footer e numeri di pagina: riconoscimento per ricorrenza | 110 | **esistente (Fase 2.4)** | `tests/unit/test_page_furniture.py` |
| `src/pdfbook/app/page_plan.py` | app | Unità di traduzione per pagina e destinazioni (con stitching) | 110 | **esistente (Fase 2)** | `tests/unit/test_app_pipeline.py` |
| `src/pdfbook/layout/tables.py` | layout | Riconoscimento tabelle dalla geometria e marcatura delle celle | 140 | **esistente (Fase 2.3)** | `tests/unit/test_tables.py` |
| `src/pdfbook/layout/styles.py` | layout | Tag `<b>`/`<i>` per gli stili inline e a capo con metriche miste | 140 | **esistente (Fase 1.1/1.2)** | `tests/unit/test_styles.py` |
| `src/pdfbook/qa/checks_visual.py` | qa | SSIM/pixel-diff originale↔output | 150 | pianificato (Fase 0) | `tests/unit/test_checks_visual.py` |
| `src/pdfbook/ocr/vlm_adapter.py` | ocr | Sidecar OCR/VLM dietro `DocumentSource` | 150 | opzionale (Fase 4) | `tests/unit/test_ocr_adapter.py` |
| `src/pdfbook/layout/aligner.py` | layout | Allineamento riga/blocco con soglie esplicite | 110 | **esistente (M7)** | `tests/unit/test_aligner.py` |
| `src/pdfbook/fonts/resolver.py` | fonts | Cascata embedded → fuzzy → sistema, copertura glifi, statistiche per il QA | 230 | **esistente (M5)** | `tests/unit/test_font_resolver.py` |
| `src/pdfbook/fonts/platform_fonts.py` | fonts | Registro font per OS: classificazione, percorsi, primo file esistente | 130 | **esistente (M5)** | `tests/unit/test_platform_fonts.py` |
| `src/pdfbook/fonts/fitz_adapter.py` | fonts | Unico punto con `fitz`: `PdfFontSource`, `make_fitz_font` | 60 | **esistente (M5)** | smoke test |
| `src/pdfbook/fonts/bundled.py` | fonts | Registro del font bundle OFL (Inter, Source Serif, Noto), ricerca su disco | 150 | **esistente (Fase 1.4)** | `tests/unit/test_bundled_fonts.py` |
| `tools/fetch_fonts.py` | tool | Scarica i font del bundle (OFL) con SHA-256, `--check` senza rete | 120 | **esistente (Fase 1.4)** | `tests/unit/test_bundled_fonts.py` |
| `tools/experiment_htmlbox.py` | tool | Confronto misurato `TextWriter` vs `insert_htmlbox` su pagina sintetica | 140 | **esistente (Fase 1.6)** | esecuzione manuale (`docs/nota-htmlbox.md`) |
| `src/pdfbook/translation/json_repair.py` | translation | Parsing JSON tollerante e riparazione | 190 | **esistente (M1)** | `tests/unit/test_json_repair.py` |
| `src/pdfbook/translation/cache.py` | translation | TM con chiave composta + scrittura atomica | 190 | **esistente (M3)** | `tests/unit/test_cache.py` |
| `src/pdfbook/translation/cache_prune.py` | translation | Potatura pura della TM per età e numero di voci | 90 | **esistente (Fase 3.5)** | `tests/unit/test_cache_prune.py` |
| `src/pdfbook/translation/style.py` | translation | Profili di stile (fedele, scorrevole, accademico, narrativo) | 90 | **esistente (Fase 5.5)** | `tests/unit/test_style_profiles.py` |
| `src/pdfbook/translation/terminology.py` | translation | Memoria terminologica per libro: propone il glossario | 140 | **esistente (Fase 5.3)** | `tests/unit/test_terminology.py` |
| `src/pdfbook/translation/chunking.py` | translation | Chunking per frase e ricomposizione dei pezzi ``chiave#i`` | 140 | **esistente (Fase 5.2)** | `tests/unit/test_chunking.py` |
| `src/pdfbook/translation/ratelimit.py` | translation | Intervallo minimo fra chiamate, thread-safe | 60 | **esistente (Fase 3.2)** | `tests/unit/test_pricing_ratelimit.py` |
| `src/pdfbook/translation/prompts.py` | translation | Prompt di traduzione e compressione (glossario, contesto troncato) | 140 | **esistente (M4)** | `tests/unit/test_prompts.py` |
| `src/pdfbook/translation/pipeline.py` | translation | Cache → chunking → provider → riparazione, con retry/backoff | 230 | **esistente (M4)** | `tests/unit/test_pipeline.py` |
| `src/pdfbook/translation/providers/base.py` | translation | Trasporto HTTP, `ProviderError`, `CompletionPort` | 100 | **esistente (M2)** | `tests/unit/test_providers.py` |
| `src/pdfbook/translation/providers/openai_compatible.py` | translation | Adapter OpenAI / DeepSeek / custom (protocollo unico) | 80 | **esistente (M2)** | `tests/unit/test_providers.py` |
| `src/pdfbook/translation/providers/gemini.py` | translation | Adapter Gemini (chiave in header) | 90 | **esistente (M2)** | `tests/unit/test_providers.py` |
| `src/pdfbook/translation/providers/anthropic.py` | translation | Adapter Claude (thinking-aware) | 80 | **esistente (M2)** | `tests/unit/test_providers.py` |
| `src/pdfbook/translation/providers/registry.py` | translation | Nome provider → istanza configurata (unico punto con gli endpoint) | 100 | **esistente (M2)** | `tests/unit/test_providers.py` |
| `src/pdfbook/rendering/canvas.py` | rendering | `TextRun` e contratto `PageCanvas` | 50 | **esistente (M9)** | `tests/unit/test_vector_renderer.py` |
| `src/pdfbook/rendering/colors.py` | rendering | intero RGB → tupla 0..1 e hex | 30 | **esistente (M9)** | `tests/unit/test_vector_renderer.py` |
| `src/pdfbook/rendering/runs.py` | rendering | Geometria pura: baseline, x, shift, altezze | 150 | **esistente (M9)** | `tests/unit/test_runs.py` |
| `src/pdfbook/rendering/painter.py` | rendering | Blocco di prosa: fit, ritraduzione compressa, issue | 230 | **esistente (M9)** | `tests/unit/test_vector_renderer.py` |
| `src/pdfbook/rendering/structured_painter.py` | rendering | Blocchi strutturati: colonne con la propria x | 110 | **esistente (M9)** | `tests/unit/test_vector_renderer.py` |
| `src/pdfbook/rendering/vector_renderer.py` | rendering | Orchestrazione di pagina: redazione, painter, shift, draw | 140 | **esistente (M9)** | `tests/unit/test_vector_renderer.py` |
| `src/pdfbook/rendering/fitz_canvas.py` | rendering | Unico punto con `fitz`: redaction + `TextWriter` per colore | 90 | **esistente (M9)** | smoke test |
| `src/pdfbook/rendering/styled.py` | rendering | Disegno con stili inline: a capo e run per parola | 160 | **esistente (Fase 1.2)** | `tests/unit/test_styles.py` |
| `src/pdfbook/rendering/shaped.py` | rendering | Shaping RTL/CJK via riquadro HTML/CSS (`insert_htmlbox`) | 120 | **esistente (Fase 4.5)** | `tests/unit/test_shaping.py` |
| `src/pdfbook/qa/report.py` | qa | Formato compatibile, scrittura atomica, `gate()` | 150 | **esistente (M10)** | `tests/unit/test_qa_report.py` |
| `src/pdfbook/qa/checks_glyphs.py` | qa | Glyph-diff atteso/reso con normalizzazione NBSP | 110 | **esistente (P0.5)** | `tests/unit/test_checks_glyphs.py` |
| `src/pdfbook/qa/checks_glossary.py` | qa | Verifica che i termini del glossario restino invariati | 80 | **esistente (Fase 5.1)** | `tests/unit/test_checks_glossary.py` |
| `src/pdfbook/qa/checks_text.py` | qa | Qualità del testo: rapporto lunghezze, ripetizioni, lingua sbagliata | 170 | **esistente (Fase 5.4)** | `tests/unit/test_checks_text.py` |
| `src/pdfbook/qa/checks_ocr.py` | qa | Confronto fra due letture OCR: divergenza e parole mancanti | 110 | **esistente (Fase 4.4)** | `tests/unit/test_checks_ocr.py` |
| `src/pdfbook/qa/checks_roundtrip.py` | qa | Round-trip del testo disegnato + conteggio NBSP/soft hyphen | 110 | **esistente (Fase 1.5)** | `tests/unit/test_checks_roundtrip.py` |
| `src/pdfbook/qa/html_report.py` | qa | Report QA in HTML statico (CSS incorporato, nessun JS) | 140 | **esistente (Fase 6.2)** | `tests/unit/test_html_report.py` |
| `src/pdfbook/qa/checks_geometry.py` | qa | Sovrapposizioni e clipping dei run disegnati | 130 | **esistente (P0.5)** | `tests/unit/test_checks_geometry.py` |
| `src/pdfbook/qa/textnorm.py` | qa | Normalizzazione del testo estratto (NBSP, soft hyphen, punteggiatura) | 90 | **esistente (P0.5)** | `tests/unit/test_textnorm.py` |
| `src/pdfbook/gui/app.py` | gui | Finestra, thread worker, progress, log | 220 | **esistente (M11)** | smoke manuale |
| `src/pdfbook/gui/config_panel.py` | gui | Pannello provider/modello/lingua/glossario | 130 | **esistente (M11)** | smoke manuale |
| `src/pdfbook/gui/presenter.py` | gui | ETA, digest issue per pagina, riepilogo run, coppie per l'anteprima | 150 | **esistente (Fase 6.1)** | `tests/unit/test_gui_presenter.py` |
| `src/pdfbook/gui/preview.py` | gui | Anteprima testo a fronte fra originale e tradotto, per pagina | 110 | **esistente (Fase 6.1)** | `tests/unit/test_gui_preview.py` |
| `src/pdfbook/gui/preview_window.py` | gui | Finestra Toplevel con selettore pagina e due colonne | 100 | **esistente (Fase 6.1)** | smoke manuale |
| `src/pdfbook/cli.py` | cli | Entrypoint argparse: `translate`, `doctor` | 160 | **esistente (M11)** | `tests/unit/test_cli.py` |
| `src/pdfbook/ocr/client.py` | ocr | Client sidecar VLM per QA/scansioni | 120 | opzionale (§14) | `test_ocr_client.py` |
| `tools/modularity_check.py` | tool | Enforcement R1/R2/R3/R5/R8/R11/R12/R13 | 300 | **esistente** | — (eseguito in CI) |
| `tools/launch.py` | tool | Avvio guidato: venv, installazione, GUI/CLI per Windows/macOS/Linux | 140 | **esistente** | `tests/unit/test_launch_tool.py` |
| `tools/check_report.py` | tool | Modello del report e stampa (separato per rispettare R1) | 80 | **esistente** | usato da `modularity_check` |
| `tests/integration/` | test | Pipeline end-to-end su PDF sintetici generati al volo (nessun binario nel repo); carico 500 pagine | — | **esistente (Fase 0/3.7)** | eseguiti in CI |
| `tests/golden/` | test | Baseline dei contatori per il confronto anti-regressione | — | **esistente (Fase 0)** | `tests/integration/test_golden.py` |

Aggiornare questa tabella è obbligatorio in ogni commit che aggiunge o sposta un modulo (R10).

---

## 4. Matrice dei layer (R5)

| \ può importare → | domain | config | qa | extraction | fonts | layout | translation | rendering | gui/cli | legacy |
|---|---|---|---|---|---|---|---|---|---|---|
| **domain** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **config** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **qa** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **extraction** | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **fonts** | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **layout** | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **translation** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **rendering** | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **gui/cli** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

---

## 5. Zona legacy e piano di migrazione

**Congelata** (R12): `legacy/**` (53 file Gen 1 già spostati dalla radice), `conversione gemini/*.py` (app in uso, eccezione dichiarata fino a M11).
Si migra **un modulo per volta**, con test verdi prima e dopo, e si elimina il sorgente legacy nella stessa PR.

| # | Migrazione | Da (righe) | A | Rischio | Dipende da |
|---|---|---|---|---|---|
| M1 | Parsing JSON | `translator.py:49-150` | `translation/json_repair.py` | basso | ✅ **fatto** (13 test) |
| M2 | Provider | `translator.py:152-263` | `translation/providers/` | basso | ✅ **fatto** (4 moduli + registry) |
| M3 | Cache | `translator.py:25-47` | `translation/cache.py` | basso | ✅ **fatto** (chiave composta, atomicità, lock) |
| M4 | Pipeline testo | `translator.py:265-427` | `translation/pipeline.py` + `prompts.py` | medio | ✅ **fatto** (chunking, retry, cache partizionata) |
| M5 | Font | `fonts.py` (tutto) | `fonts/resolver.py` + `platform_fonts.py` + `fitz_adapter.py` | medio | ✅ **fatto** (19 test + smoke su PDF reale) |
| M6 | Fitting | `rebuild_vector.py:73-228,272-280` | `layout/fitter.py` + `hyphenation.py` + `toc.py` | medio | ✅ **fatto** (37 test) |
| M7 | Segmentazione/align. | `rebuild_vector.py:33-63,156-188` | `layout/segmentation.py` + `aligner.py` | basso | ✅ **fatto** (+ `toc.py` in M6, 30 test) |
| M8 | Estrazione | `rebuild_vector.py:283-410` | `extraction/pdf_extractor.py` + `fitz_source.py` | alto | ✅ **fatto** (16 test + smoke su PDF reale) |
| M9 | Rendering | `rebuild_vector.py:410-700` | `rendering/` (6 moduli) | alto | ✅ **fatto** (26 test + smoke) |
| M10 | QA | `rebuild_vector.py:317-330,700-730` | `qa/report.py` | basso | ✅ **fatto** (formato compatibile + gate) |
| M11 | GUI/config | `app_gui.py` | `gui/` + `config/settings.py` + `app/` + `cli.py` | medio | ✅ **fatto** (272 test complessivi) |

Regola pratica: ogni riga della tabella è **una PR**, con mapping riga-per-riga verificato da un test golden (stesso output su 3 pagine campione).

Fino a M10 il sorgente Gen 2 (`conversione gemini/`) resta **attivo e necessario**: i nuovi moduli vengono collegati in M11 e solo allora si rimuovono `translator.py`, `fonts.py`, `rebuild_vector.py`, `app_gui.py`.

---

## 6. Indice della documentazione

| Documento | Contenuto | Quando leggerlo |
|---|---|---|
| [`AGENTS.md`](../AGENTS.md) | regole vincolanti, Definition of Done | sempre, prima di iniziare |
| `docs/MODULE_MAP.md` (questo file) | routing, registro moduli, migrazioni | sempre, per orientarsi |
| `docs/architecture/README.md` | indice dell'architettura per sezioni | per capire il "perché" |
| `docs/architecture/01-contesto.md` | obiettivi, vincoli, due generazioni | nuovo contributore |
| `docs/architecture/02-inventario-stack.md` | cosa c'è, con cosa è fatto | inventario |
| `docs/architecture/03-architettura-gen2.md` | moduli, thread, stato | interventi trasversali |
| `docs/architecture/04-pipeline.md` | flusso end-to-end in 8 passi | debugging funzionale |
| `docs/architecture/05-algoritmi.md` | font cascade, fitting, sillabazione, feedback LLM, parsing | modifiche algoritmiche |
| `docs/architecture/06-modello-dati.md` | JSON di traduzioni, cache, config, QA | cambi di formato |
| `docs/architecture/07-config-build.md` | configurazione, PyInstaller, esecuzione | packaging |
| `docs/architecture/08-qualita.md` | metriche misurate sui libri reali | valutare una regressione |
| `docs/architecture/09-difetti.md` | bug e debito noti con riferimenti | prima di "sistemare" qualcosa |
| `docs/architecture/10-valutazione-target.md` | giudizio e architettura target | decisioni di design |
| `docs/architecture/11-unlimited-ocr.md` | valutazione VLM/OCR e QA visivo | roadmap qualità |
| `docs/architecture/12-appendici.md` | simboli, costanti, glossario | riferimento rapido |
| `docs/modules/<modulo>.md` | contratto di un singolo modulo | quando tocchi quel modulo |
| [`SECURITY.md`](../SECURITY.md) | segreti, rotazione chiavi, segnalazioni | prima di ogni push |
| [`docs/ROADMAP.md`](ROADMAP.md) | piano di implementazione a fasi, metriche target, rischi | prima di scegliere cosa fare |

---

## 7. Come aggiungo un modulo

Vedi R9 in `AGENTS.md`. Riassunto: file nel layer corretto → riga nella tabella §3 → `docs/modules/<modulo>.md` → test → `py tools/modularity_check.py`.
