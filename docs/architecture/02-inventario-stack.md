# Inventario del repository e stack

> Parte dell'architettura: indice in [`README.md`](README.md). Sezioni 3, 4.
> Regole vincolanti: [`AGENTS.md`](../../AGENTS.md).

---

## 3. Inventario del repository

### 3.1 Mappa delle directory

> **Nota sullo stato attuale.** Questa mappa documenta il repository **al momento dell'analisi**
> (due generazioni di pipeline). Dopo la migrazione il progetto pubblicato contiene solo
> `src/pdfbook/`, `docs/`, `tests/`, `tools/`, `legacy/` e i file di progetto (≈0,5 MB):
> i dati editoriali (PDF, traduzioni, cache, render di test) e l'app Gen 2 sono stati
> **rimossi dal progetto** e non sono conservati. Le voci sotto restano come documentazione storica.

```
traduzione libri/
├── conversione gemini/           ← app Gen 2, congelata (rimossa dopo la migrazione)
│   ├── app_gui.py                GUI CustomTkinter (entrypoint storico)
│   ├── translator.py             adapter multi-provider LLM + cache + parsing robusto
│   ├── rebuild_vector.py         motore di ricostruzione PDF vettoriale
│   ├── fonts.py                  FontManager (riuso font embedded + fallback di sistema)
│   ├── config.json               configurazione persistente (⚠ contiene API key in chiaro)
│   ├── translations_cache.json   translation memory (5952 voci, md5→testo)
│   ├── app_gui.spec              build PyInstaller (onefile, windowed)
│   ├── dist/app_gui.exe          binario distribuito (42,2 MB)
│   ├── build/                    artefatti PyInstaller (≈50 MB)
│   ├── test_run.py               test offline del renderer raster legacy
│   ├── test_vector_run.py        test offline del renderer vettoriale (monkeypatch del traduttore)
│   └── Test_*.pdf / *_qa_report.json   artefatti di collaudo
│
├── *.pdf                         libri sorgente e output (324 e 365 pagine)
├── translations.json             TM Gen 1 (2.742 blocchi, chiavi p{page}_b{idx})
├── batch_p*_...json              lotti di lavoro Gen 1 (input/output manuali)
├── extracted_text.json           dump strutturale del PDF Patton (324 pagine, 7,2 MB)
├── rebuild_v2…v9 / _pil / _hq / _final / _redact / _pdf   renderer storici (Gen 1)
├── build_and_apply.py, translate_batch.py, final_translate.py, translations_data.py,
│   apply_translations.py, fix_remaining.py               "traduttori" Gen 1 (dizionari inline)
├── create_batch*.py, pages_needing_translation.py, show_*.py, check_*.py,
│   verify_*.py, test_*.py                                tooling di ispezione/QA Gen 1
└── test_output/                  render PNG di confronto visivo originale/tradotto
```

### 3.2 Classificazione dei file Python (59 file: 53 in radice + 6 in `conversione gemini/`)

| Categoria | File | Ruolo | Stato |
|---|---|---|---|
| **Core Gen 2** | `app_gui.py`, `translator.py`, `rebuild_vector.py`, `fonts.py` | prodotto | attivo |
| **Renderer storici** | `rebuild_v2.py … rebuild_v9.py`, `rebuild_pdf.py`, `rebuild_pil.py`, `rebuild_hq.py`, `rebuild_final.py`, `rebuild_redact.py` | tentativi di conservazione layout | superati |
| **Autoring traduzioni** | `build_and_apply.py`, `translate_batch.py`, `final_translate.py`, `translations_data.py`, `fix_remaining.py` | script-monolite con dizionari di traduzione **inline** | esauriti |
| **Estrattori** | `extract_to_json.py`, `extract_all.py`, `explore_pdf.py`, `check_json.py` | dump del PDF | usa-e-getta |
| **Batch manager** | `create_batch.py`, `create_batch_v2.py`, `pages_needing_translation.py`, `apply_translations.py`, `show_untranslated.py`, `show_page.py`, `show_original_by_page.py` | frammentazione del lavoro in lotti | usa-e-getta |
| **Verificatori** | `check_italian.py`, `check_quality.py`, `check_spacing.py`, `check_translations.py`, `check_v8.py`, `check_p6.py`, `verify_*.py` | QA euristico post-hoc | usa-e-getta |
| **Sonde tecniche** | `test_pixmap*.py`, `test_native*.py`, `test_reconstruct.py`, `test_visual.py`, `test_approach.py`, `render_samples.py` | esperimenti su API PyMuPDF/PIL | usa-e-getta |

**Osservazione architetturale chiave**: la radice del repository è un *lab notebook*, non un codebase. La Gen 2 è invece un piccolo codebase coerente (4 moduli, ≈1.960 righe) che meriterebbe di essere isolato in un package con test e dipendenze dichiarate.

---


---

## 4. Stack tecnologico

| Livello | Tecnologia | Versione rilevata | Note |
|---|---|---|---|
| Runtime | CPython | 3.14.0 | `conversione gemini/__pycache__` con tag `cpython-314` |
| PDF engine | **PyMuPDF** (`fitz`) | 1.28.0 | estrazione blocchi/spans, redaction, `TextWriter`, `extract_font`, `subset_fonts` |
| GUI | **CustomTkinter** | 6.0.0 | tema dark, layout a griglia |
| HTTP | `requests` | 2.34.2 | chiamate sincrone, timeout 60 s |
| Sillabazione | **pyphen** | 0.17.2 | dizionari `it_IT`, `en_US`, `es`, `fr`, `de_DE` |
| Imaging (legacy) | Pillow | 12.3.0 | solo per i renderer raster Gen 1 |
| Packaging | PyInstaller | 6.21.0 (+ hooks 2026.6) | `--onefile --windowed`, UPX attivo |
| LLM | Gemini / OpenAI / DeepSeek / Anthropic / OpenAI-compatibile | — | HTTP diretto, nessun SDK |

**Dipendenze non dichiarate**: non esiste `requirements.txt`, `pyproject.toml`, `environment.yml` né lockfile. `pyphen` è opzionale (import protetto con `PYPHEN_OK`), ma il degrado non è segnalato all'utente in modo esplicito.

---
