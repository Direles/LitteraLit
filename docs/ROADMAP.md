# Piano di implementazione — da strumento valido a strumento premium

> Documento di pianificazione. Regole: [`AGENTS.md`](../AGENTS.md). Routing: [`MODULE_MAP.md`](MODULE_MAP.md).
> Stato di partenza: M1–M11 chiusi, P0.5 chiuso, **316 test**, gate di struttura a 0 errori, CI verde.
> Questo piano definisce *cosa* manca, *in che ordine*, *come si misura* che sia servito.

---

## 1. Cosa significa "premium e affidabile" (criteri misurabili)

Senza numeri, "premium" è un'opinione. Questi sono i target che ogni fase deve rispettare.

| Dimensione | Metrica | Baseline oggi | Target premium |
|---|---|---|---|
| Impaginazione | `perfect` su libri reali | 97,7% (Cohn, 4.207 blocchi) | **≥ 99%** |
| Riduzione corpo | `font_reduced` | 48,6% | **≤ 20%** |
| Sforamento | `overflow_shifted` | 26% | **≤ 8%** |
| Sovrapposizioni | `text_overlap` / `clipped` per 100 pagine | 17,8 + 7,1 (legacy) | **≤ 1 + 1** |
| Glifi | `glyph_missing` | 4→0 su 1 pagina campione | **0** su ogni libro |
| Fedeltà visiva | SSIM originale↔output | non misurato | **≥ 0,97** media pagina |
| Testo estratto | round-trip caratteri (dopo normalizzazione) | ~99% (NBSP residui) | **≥ 99,9%**, zero NBSP/soft-hyphen |
| Affidabilità run | eccezioni non gestite su 500 pagine | non testato | **0** |
| Ripresa | pagine duplicate dopo interruzione | impossibile (no resume) | **0** |
| Onestà | fallback silenziosi | 0 nel codice nuovo | **0** (gate bloccante) |
| Costo | tracciamento token/euro per run | assente | **100%** delle chiamate |

"Affidabile" significa anche: **nessun difetto silenzioso**. Ogni deviazione diventa una `QAIssue` che il gate può bloccare.

---

## 2. Principi di esecuzione

1. **Misura prima di migliorare**: nessuna ottimizzazione tipografica senza una metrica che la validi (Fase 0 è propedeutica a tutto).
2. **Una PR = una fase piccola**, con test e documentazione aggiornata (R15).
3. **Nessuna regressione silenziosa**: il gate QA e i golden report falliscono la CI.
4. **Adapter dietro `Protocol`**: ogni nuovo motore (OCR, tabelle, flow) entra come modulo, non come innesto nel renderer.
5. **Licenza come vincolo di design**: PyMuPDF è AGPL; ogni dipendenza nuova passa da `pip-licenses` in CI.

---

## Fase 0 — Fondamenta di misura (≈5 giorni) · *prerequisito*

| # | Deliverable | File | Stato |
|---|---|---|---|
| 0.1 | Confronto visivo originale↔output: SSIM, densità inchiostro, mappa di diff per pagina | `src/pdfbook/qa/checks_visual.py` | ✅ **fatto** (19 test) |
| 0.2 | Issue `VISUAL_DRIFT` con soglia configurabile, integrata nel report | `qa/report.py` (nuovo `IssueKind`) | ✅ **fatto** (informativa, non bloccante) |
| 0.3 | Fixture PDF **sintetiche** (licenza pulita): nativo semplice, 2 colonne, indice, tabella, scansione simulata | `tests/integration/` (generate al volo, nessun binario nel repo) | ⏳ **parziale** (nativo semplice; mancano colonne/indice/tabella) |
| 0.4 | Test golden: pipeline con provider finto → snapshot del report QA (JSON normalizzato) | `tests/integration/test_golden.py` | ✅ **fatto** (5 test) |
| 0.5 | Baseline metriche per fixture, usata come soglia di regressione in CI | `tests/golden/baseline.json` | ✅ **fatto** |
| 0.6 | CI: "regressione visiva" + `pip-licenses` + `gitleaks` | `.github/workflows/ci.yml` | ✅ **parziale**: golden+integrazione girano in CI, aggiunto `--secrets-only`; **audit licenze rinviato alla 6.5** (PyMuPDF è AGPL: fallirebbe subito) |

**Accettazione**: una modifica al renderer che peggiora SSIM oltre 0,01 fa fallire la CI.

**Stato**: 0.1 e 0.2 chiusi. Il confronto è stato reso **mascherato** (SSIM fuori dalle aree di
testo, mappa dell'inchiostro per riquadri): un SSIM globale originale↔tradotto non avrebbe
senso, perché la lingua cambia i glifi. Restano 0.3–0.6 (fixture multiple, golden, licenze/segreti).

**Rischio**: font non deterministici fra macchine → SSIM rumoroso. Mitigazione: Fase 1.4 (font bundle).

---

## Fase 1 — Fedeltà tipografica (≈10 giorni)

| # | Deliverable | File | Note |
|---|---|---|---|
| 1.1 | Estrazione **per run tipografico** (`rawdict`/`get_texttrace`): bold, italic, colore e corpo per run, non solo per blocco | `extraction/pdf_extractor.py`, `domain/models.py` (`TextRun` semantico) | **fatto**: round-trip a marcatori (`layout/styles.py`), vedi §11.6 |
| 1.2 | Rendering multi-run: una riga può avere più font/colori; corsivo e grassetto conservati | `rendering/runs.py`, `painter.py` | **fatto**: `rendering/styled.py`, fallback `style_flattened` |
| 1.3 | Apici/apici di nota: shift di baseline e corpo ridotto, senza declassare il blocco | `rendering/painter.py`, `layout/fitter.py` | **fatto**: `layout/scripts.py` + tag `<sup>`/`<sub>` |
| 1.4 | Font bundle liberi (Inter, Source Serif, Noto Serif/Sans) + fallback deterministico, via `data/fonts/` | `fonts/platform_fonts.py` | rende stabili i golden e indipendenti dall'OS |
| 1.5 | **ToUnicode custom** con `fontTools`: elimina NBSP/soft-hyphen nel testo estratto | `rendering/fitz_canvas.py` | chiude §11.7/1 |
| 1.6 | Sperimentazione `insert_htmlbox`/`Story` per giustificazione e sillabazione CSS, dietro flag, valutata con 0.1 | `rendering/flow_renderer.py` | decisione go/no-go con numeri |

**Accettazione**: fixture mista → SSIM ≥ 0,97, round-trip caratteri ≥ 99,9%, `font_reduced` dimezzato.

**Ordine interno**: 1.4 → 1.1 → 1.2 → 1.3 → 1.5 → 1.6 (il font bundle prima, per non rincorrere rumore).

---

## Fase 2 — Struttura e flusso del testo (≈10 giorni)

| # | Deliverable | File | Note |
|---|---|---|---|
| 2.1 | **Paragraph stitching** fra pagine: rilevamento continuazione, traduzione unica, ridistribuzione sui due box | `layout/flow.py`, `app/page_plan.py` | ✅ **fatto** (14 test + 3 end-to-end) |
| 2.2 | Issue `PARAGRAPH_STITCHED` (informativa) e `SPLIT_FAILED` (bloccante) | `domain/models.py`, `qa/report.py` | ✅ **fatto** (SPLIT_FAILED nel gate) |
| 2.3 | Tabelle: rilevamento geometrico delle celle e rendering vincolato alla cella | `layout/tables.py`, `rendering/painter.py` | ✅ **fatto** (11 test; issue `table_misaligned`) |
| 2.4 | Header/footer/numero pagina: classificati e **non** tradotti | `layout/page_furniture.py`, `app/page_plan.py` | ✅ **fatto** (10 test) |
| 2.5 | Ordine di lettura multi-colonna: colonne vere, non solo righe affiancate | `layout/segmentation.py` | **fatto**: `layout/columns.py`, fallback prudente |
| 2.6 | Note a piè di pagina: riferimento apice ↔ nota, gruppo mantenuto insieme | `layout/notes.py` | **fatto**: `BlockKind.FOOTNOTE`, note escluse dallo stitching |

**Accettazione**: fixture "2 colonne + tabella + nota" senza issue bloccanti; libro Patton: zero frammenti che iniziano minuscoli a inizio pagina dopo lo stitching.

---

## Fase 3 — Robustezza operativa (≈8 giorni)

| # | Deliverable | File | Note |
|---|---|---|---|
| 3.1 | **Checkpoint/resume**: journal con fingerprint, cache salvata ogni N pagine, `--resume` | `app/checkpoints.py`, `app/journal.py` | ✅ **fatto** (ripresa con 0 chiamate duplicate, verificata da test) |
| 3.2 | Parallelismo controllato dei chunk + rate limiter + `Retry-After` | `translation/ratelimit.py`, `translation/pipeline.py` | ✅ **fatto** (workers opt-in; le pagine restano sequenziali per via dello stitching) |
| 3.3 | **Tracking costi/token** per pagina e per run, con `--max-cost` | `config/pricing.py`, `app/costs.py` | ✅ **fatto** (stima indicativa, tetto bloccante, ripresa possibile) |
| 3.4 | Tassonomia errori utente: codici di uscita stabili e messaggi con il rimedio | `app/errors.py`, `cli.py`, `gui/app.py` | ✅ **fatto** (8 test) |
| 3.5 | Cache: TTL/versione, `pdfbook cache`, export TM per documento | `translation/cache.py`, `cli.py` | **fatto**: timestamp per voce, `pdfbook cache [--prune --max-age --max-entries]`; export TM ancora da fare |
| 3.6 | Log strutturato su file con rotazione; nessun `print` in produzione | `config/logging.py` | |
| 3.7 | Test di robustezza: 500 pagine sintetiche, 429 indotti, interruzione a metà | `tests/integration/` | **fatto**: `test_stress.py` (500 pagine, workers=4, ripresa a costo zero); 429 coperto da `test_pricing_ratelimit` |

**Accettazione**: interruzione forzata → ripresa senza duplicati; run da 500 pagine con zero eccezioni non gestite sotto errori indotti.

---

## Fase 4 — OCR e scansioni (≈12 giorni, opzionale ma richiesto dal mercato)

| # | Deliverable | File | Note |
|---|---|---|---|
| 4.1 | Layer `ocr/` con `OcrSource` che implementa `DocumentSource` | `src/pdfbook/ocr/` | **parziale**: riconoscimento scansioni (`extraction/scan_detect.py`) e messaggio azionabile; l'adapter `OcrSource` richiede i binari (4.2) |
| 4.2 | Adapter **ocrmypdf + Tesseract** (CPU): text layer invisibile → la pipeline esistente funziona senza modifiche | `ocr/ocrmypdf_adapter.py` | primo passo economico |
| 4.3 | Adapter **VLM sidecar** (SGLang OpenAI-compatible), parser `<\|det\|>tipo [bbox]` | `ocr/vlm_adapter.py`, `ocr/det_parser.py` | riusa il formato di Unlimited-OCR |
| 4.4 | QA visivo anche per scansioni: `SCAN_FALLBACK`, confronto con OCR indipendente | `qa/checks_ocr.py` | l'OCR come giudice, non come estrattore |
| 4.5 | Scritture RTL/CJK: HarfBuzz + Noto, test sintetici | `fonts/`, `rendering/` | nuova classe di libri |

**Accettazione**: fixture scansionata → traduzione con gate PASS; pagina araba/cinese renderizzata senza glifi mancanti.

---

## Fase 5 — Qualità della traduzione (≈8 giorni)

| # | Deliverable | File | Note |
|---|---|---|---|
| 5.1 | Glossario **vincolante**: verifica dei termini presenti nell'originale e assenti nella traduzione (issue informativa) | `qa/checks_glossary.py`, `app/pipeline.py` | ✅ **fatto** (8 test, senza dipendenze nuove) |
| 5.2 | Chunking per frase (`stanza`/`spaCy`) e contesto scorrevole su 2 pagine | `translation/chunking.py` | coerenza migliore |
| 5.3 | Memoria terminologica per libro (termini ricorrenti → glossario automatico proposto) | `translation/terminology.py` | |
| 5.4 | Controlli di qualità del testo: ripetizioni, omissioni (rapporto lunghezze), lingua sbagliata (`langid`), LanguageTool come informativa | `qa/checks_text.py` | **fatto** (senza dipendenze, lingua via stopword); LanguageTool ancora da fare |
| 5.5 | Profili di stile per libro (formale/informale, "non tradurre") | `config/settings.py` | **fatto**: `translation/style.py` + `PDFBOOK_STYLE` (fedele, scorrevole, accademico, narrativo) |

**Accettazione**: glossario rispettato al 100% su fixture con termini obbligatori; rilevamento di un'omissione seminata.

---

## Fase 6 — Prodotto (≈10 giorni)

| # | Deliverable | Note |
|---|---|---|
| 6.1 | GUI: anteprima prima/dopo con diff, ispettore issue per pagina, resume, drag & drop, ETA, annulla | oggi la GUI è funzionale ma "cieca" sull'output |
| 6.2 | CLI: `pdfbook qa`, `report --html`, `batch` su più file | | **parziale**: `pdfbook qa` e `pdfbook report` (HTML statico); `batch` ancora da fare |
| 6.3 | Packaging multi-OS in CI (PyInstaller matrix), release firmate Windows, AppImage Linux | oggi c'è solo il lanciatore |
| 6.4 | Guida utente con screenshot, troubleshooting, FAQ, video breve | docs/ |
| 6.5 | **Decisione licenza**: sostituire PyMuPDF (pypdfium2 + pdfminer/pdfplumber + pikepdf + ReportLab) oppure accettare AGPL | blocca la distribuzione commerciale |

**Accettazione**: macchina pulita → doppio clic → traduzione → gate PASS, senza terminale; artefatti in GitHub Releases.

---

## Fase 7 — Scala e osservabilità (≈5 giorni)

- metriche per run (pagine/min, token, costo, issue per tipo) e sommario HTML;
- budget di performance: 500 pagine senza superare 4 GB RAM;
- test di carico su libro grande; documentazione degli SLO nel README.

---

## 3. Ordine di esecuzione e sequenza PR

| Ordine | PR | Dipende da | Durata |
|---|---|---|---|
| 1 | QA visivo + fixture + golden (Fase 0) | — | 5 gg |
| 2 | Font bundle + run tipografici + rendering multi-run (1.4, 1.1, 1.2) | 1 | 6 gg |
| 3 | Apici + ToUnicode custom (1.3, 1.5) | 2 | 4 gg |
| 4 | **Paragraph stitching** (2.1, 2.2) | 1 | 3 gg |
| 5 | Tabelle, header/footer, colonne (2.3–2.5) | 2 | 7 gg |
| 6 | Checkpoint + parallelismo + costi (3.1–3.3) | — | 5 gg |
| 7 | Errori utente, cache, logging (3.4–3.6) | 6 | 3 gg |
| 8 | Note a piè di pagina (2.6) | 3 | 3 gg |
| 9 | Glossario + chunking + QA testo (5.1, 5.2, 5.4) | 4 | 5 gg |
| 10 | GUI prodotto + report HTML (6.1, 6.2) | 6,7 | 6 gg |
| 11 | OCR: ocrmypdf, poi sidecar VLM (4.1–4.4) | 5 | 12 gg |
| 12 | Packaging multi-OS + release (6.3) | 10 | 4 gg |
| 13 | RTL/CJK (4.5) e osservabilità (Fase 7) | 11 | 6 gg |

**Criticità**: la riga 1 (misura) non è comprimibile; la riga 11 (OCR) è l'unica che si può rimandare senza degradare i libri nativi.

---

## 4. Strategia di test (per fase)

| Livello | Cosa | Dove |
|---|---|---|
| Unit | logica pura: fitter, flow, parsing, cache, gate | `tests/unit/` (oggi 316) |
| Contract | ogni adapter rispetta il suo `Protocol` | `tests/contract/` |
| Integrazione | pipeline completa su fixture PDF sintetiche con provider finto | `tests/integration/` |
| Golden | report QA e metriche visive confrontati con baseline | `tests/golden/` |
| Robustezza | 429/timeout/interruzioni/PDF corrotti | `tests/integration/` |
| Licenza/segreti | `pip-licenses`, `gitleaks` | CI |

Regola: un bug corretto senza test di regressione **non è corretto** (R7).

---

## 5. Rischi e mitigazioni

| Rischio | Impatto | Mitigazione |
|---|---|---|
| PyMuPDF AGPL blocca la distribuzione | alto | Fase 6.5: decisione esplicita, con piano B pypdfium2+ReportLab |
| SSIM instabile fra macchine | medio | font bundle (1.4) e tolleranze per pagina |
| Stitching errato (unisce paragrafi non correlati) | medio | euristiche conservative + `SPLIT_FAILED` + ispezione in GUI |
| OCR/VLM costoso e pesante | medio | ocrmypdf prima; VLM solo per scansioni, in sidecar |
| Scope creep tipografico | alto | ogni feature deve migliorare una metrica della §1 |
| Tempo: piano da ~10 settimane | alto | priorità rigida: 0→1→2→3 prima di 4/5/6 |

---

## 6. Cosa NON fare

- Riscrivere il renderer come HTML→PDF completo: si perde la grafica vettoriale originale.
- Usare un VLM come estrattore primario sui PDF nativi: si perdono font/corpo/colore.
- Aggiungere dipendenze senza controllo licenze.
- Introdurre eccezioni silenziose per "far passare" una fixture.

---

## 7. Definizione di "pronto" per ogni fase

1. Metriche della §1 rispettate o migliorate, con numeri nel commit.
2. `modularity_check --strict` a 0 errori, 0 warning.
3. Test nuovi + golden aggiornati con motivazione.
4. `docs/modules/<modulo>.md` aggiornato e riga in `MODULE_MAP`.
5. Nessuna nuova dipendenza senza nota di licenza.
