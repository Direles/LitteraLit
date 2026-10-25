# Valutazione e architettura target

> Parte dell'architettura: indice in [`README.md`](README.md). Sezioni 12, 13.
> Regole vincolanti: [`AGENTS.md`](../../AGENTS.md).

---

## 12. Valutazione architetturale complessiva

### 12.1 Punti di forza (reali, non di facciata)

1. **Approccio vettoriale corretto**: redazione senza distruggere immagini/grafica + `TextWriter` con font reali. È la scelta tecnicamente giusta; il 97,7% di blocchi "in riga" e l'output a 2,8 MB lo confermano.
2. **Metriche tipografiche reali** invece di coefficienti empirici: `font.text_length` elimina la classe di errori "testo che sborda perché ho stimato male la larghezza".
3. **Riuso dei font embedded con verifica di copertura glifi**: soluzione elegante e rara, che preserva l'identità tipografica del libro quando il PDF lo consente.
4. **Sillabazione linguistica** (pyphen) nel word-wrap.
5. **Loop di feedback layout→LLM** (`translate_shorter`) e **rilevamento/retry dei non tradotti**: due controlli di qualità che nella maggior parte dei tool analoghi non esistono.
6. **Parsing JSON a degradazione controllata** + salvataggio del payload fallito: pragmatismo efficace contro l'inaffidabilità dei modelli.
7. **Report QA machine-readable**: rende misurabile la qualità e consente una futura automazione della revisione.
8. **Multi-provider con discovery dei modelli**: evita l'obsolescenza hardcoded dei nomi modello (problema reale, ben documentato nel commento su Anthropic).
9. **Thread-safety della GUI** rispettata (worker daemon + `after`).

### 12.2 Debolezze strutturali

1. **Monolite procedurale**: `process_pdf_vector` è una funzione di ~380 righe con 8 responsabilità (estrazione, batching, redazione, fitting, allineamento, shift, salvataggio, QA). Non testabile in isolamento.
2. **Nessun confine di interfaccia** verso il traduttore (import diretto + monkeypatch nei test).
3. **Nessuna astrazione "Documento/Blocco/Riga"**: si lavora su dizionari PyMuPDF non tipizzati, con chiavi stringa (`bbox`, `origin_y`, `spans`) sparse nel codice.
4. **Configurazione come `dict` non validato**: chiavi opzionali gestite con `.get` sparsi, nessun dataclass/schema.
5. **Assenza totale di test automatici, CI, linting, type checking**.
6. **Assenza di separazione Gen 1 / Gen 2**: 53 script storici nella stessa cartella del prodotto attuale.
7. **Osservabilità assente**: nessun log strutturato, nessuna metrica di durata, nessun tracciamento dei costi API.

### 12.3 Giudizio sintetico

| Dimensione | Voto | Motivazione |
|---|---|---|
| Idea e algoritmi | **8/10** | vettoriale + font matching + sillabazione + feedback layout→LLM |
| Qualità output | **7,5/10** | layout rispettato nel 97,7% dei blocchi; stile inline e tabelle persi |
| Robustezza | **4/10** | nessun retry/backoff, nessun checkpoint, errori bloccanti |
| Ingegnerizzazione | **3/10** | no VCS, no test, no deps, no log, no tipi |
| Sicurezza | **2/10** | API key in chiaro nel repo, key in query string |
| Manutenibilità | **3/10** | 13 renderer duplicati, funzioni monolitiche, script usa-e-getta |
| Distribuzione | **6/10** | eseguibile funzionante, ma onefile non firmato e senza log |

**Sintesi**: un *prototipo avanzato di ricerca applicata* con intuizioni migliori di molti prodotti commerciali, ma con un involucro di ingegneria ancora artigianale. Il valore è tutto negli algoritmi; il rischio è tutto nella gestione del ciclo di vita.

---


---

## 13. Architettura target proposta

### 13.1 Struttura di package

```
pdfbook-translator/
├── pyproject.toml                 # deps + tool config (ruff, mypy, pytest)
├── README.md
├── src/pdfbook/
│   ├── cli.py                     # entrypoint Typer/argparse
│   ├── gui/app.py                 # CustomTkinter (solo presentation)
│   ├── domain/
│   │   ├── models.py              # dataclass: Document, Page, Block, Line, Span, Settings
│   │   └── ports.py               # Protocol: Translator, FontResolver, Renderer, ProgressSink
│   ├── extraction/pdf_extractor.py
│   ├── layout/
│   │   ├── segmentation.py        # TOC/multi-column/table detection
│   │   ├── fitter.py              # fit_font, wrap_text, hyphenation
│   │   └── aligner.py
│   ├── rendering/vector_renderer.py
│   ├── fonts/resolver.py          # FontManager + registry piattaforma
│   ├── translation/
│   │   ├── providers/{gemini,openai,deepseek,anthropic,custom}.py
│   │   ├── cache.py               # chiave composta (hash testo+provider+model+lang)
│   │   ├── json_repair.py
│   │   └── pipeline.py            # batching, retry, backoff, rate limit, chunking
│   ├── qa/report.py               # schema tipizzato + validazione
│   └── config/settings.py         # pydantic settings, secrets da env/keyring
├── tests/
│   ├── unit/                      # json_repair, fitter, toc regex, cache key
│   ├── golden/                    # 10 PDF fixture + snapshot QA report
│   └── e2e/                       # mock provider HTTP (responses)
└── legacy/                        # archivio Gen 1 (sola lettura, fuori dal build)
```

### 13.2 Principi di rifattorizzazione

1. **Estrarre i seam**: `Translator`, `FontResolver`, `Renderer`, `ProgressSink` come `Protocol`; iniezione dal chiamante (elimina i monkeypatch e abilita test offline reali).
2. **Spezzare `process_pdf_vector`** in 5 fasi pure: `extract() → segment() → translate() → layout() → render()`, ciascuna con input/output dataclass. La funzione di orchestrazione scende a ~60 righe.
3. **Rendere il QA un contratto**: JSON Schema + validazione + soglie di accettazione (es. `perfect ≥ 95%`, `untranslated_unresolved == 0`) usabili in CI come *quality gate*.
4. **Checkpoint per pagina**: salvataggio incrementale (`doc.save(out, incremental=True, encryption=…)`) o journal `page_state.json` → resume dopo crash.
5. **Resilienza rete**: retry con backoff esponenziale + jitter su `429/5xx/timeout`, `Retry-After` rispettato, rate limiter token-bucket per provider, chunking del batch per numero di caratteri (es. 6.000 char/richiesta).
6. **Cache a chiave composta**: `sha256(provider|model|target_lang|glossary_hash|text)`; TTL/versione dello schema; comando `cache prune`; esportazione per documento (`<book>.tm.json`).
7. **Logging strutturato** (`structlog`/`logging` JSON) su file con rotazione, più `--verbose`; eliminazione progressiva dei `print`.
8. **Segreti**: `keyring`/DPAPI, mai in `config.json`, mai in query string; `.gitignore` per `*.json` di config e per gli output.
9. **Cross-platform font registry**: `platformdirs` + font di sistema per OS, font bundle opzionali (es. Inter/Source Serif) per garantire copertura glifi.
10. **Concorrenza controllata**: 3–6 pagine in parallelo con `ThreadPoolExecutor` (le chiamate sono I/O bound), sincronizzazione sulla cache, progress bar monotona.
11. **Estensioni funzionali**: tabella come entità, spans tipizzati per conservare bold/italic, apici/note, OCR fallback (Tesseract) con `pytesseract` per i PDF scansionati, glossario con traduzione imposta.

### 13.3 Roadmap suggerita

| Fase | Contenuto | Sforzo stimato | Valore |
|---|---|---|---|
| **P0 — Igiene** | revoca/rotazione chiavi, `.gitignore`, `git init`, `requirements.txt`/`pyproject.toml`, spostare Gen 1 in `legacy/`, fix bug §11.2 (1, 5), rimozione `still_untranslated` leak | 2–3 gg | 🔴 sblocca tutto il resto |
| **P0.5 — QA low-cost** | QA geometrico (overlap/clipping) + glyph-diff sul testo estratto dall'output — nessuna GPU, nessun modello nuovo (§14.7) | ~1 gg | 🔴 cattura i difetti oggi invisibili |
| **P1 — Robustezza** | retry/backoff, logging su file, checkpoint per pagina, validazione config (pydantic), rimozione `print` | 4–6 gg | 🔴 run lunghe affidabili |
| **P2 — Testabilità** | estrazione `src/`, `Protocol` per Translator/FontResolver, test unitari su `json_repair`/`fitter`/regex TOC, golden PDF | 5–8 gg | 🟠 regressioni sotto controllo |
| **P3 — Qualità output** | conservazione inline styles (bold/italic), colori per riga TOC, gestione tabelle, clamp bordo pagina | 6–10 gg | 🟠 output "da pubblicazione" |
| **P4 — Throughput** | parallelismo pagine, rate limiter, chunking batch, cache a chiave composta, cost tracking | 4–6 gg | 🟡 3–5× più veloce |
| **P5 — Estensioni** | OCR/VLM end-to-end come oracolo QA e per PDF scansionati (vedi §14), glossario con traduzione imposta, QA gate in CI, editor di revisione | 2–3 settimane | 🟢 nuovo mercato/uso |

---
