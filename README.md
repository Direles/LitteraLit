# PDF Book Translator

[![ci](https://github.com/Direles/LitteraLit/actions/workflows/ci.yml/badge.svg)](https://github.com/Direles/LitteraLit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Traduce libri tecnici in PDF **conservando il layout**: redazione vettoriale del testo originale, riuso dei font embedded, sillabazione nella lingua di destinazione, adattamento tipografico con metriche reali e un report QA per pagina.

> **Stato**: migrazione **completata** (M1–M11) e codice pubblicato. Il progetto vive in
> `src/pdfbook/` (moduli con budget dimensionali e test) e in `docs/`; `legacy/` conserva il
> codice Gen 1 congelato. **Dati editoriali e app precedente non fanno parte del progetto**:
> sono stati rimossi e non sono conservati nel repository.

## Cosa fa

| Passo | Cosa succede |
|---|---|
| 1 | Estrae blocchi, righe e span dal PDF (font, corpo, colore, posizione) |
| 2 | Traduce **una pagina per richiesta** via LLM (Gemini, OpenAI, DeepSeek, Claude o endpoint OpenAI-compatibile), con glossario e contesto della pagina precedente |
| 3 | Rileva e ritraduce i blocchi rimasti in inglese |
| 4 | Rimuove il testo originale con redazione vettoriale (immagini e grafica restano intatte) |
| 5 | Ricompone il testo con i font originali o TTF equivalenti, sillabazione inclusa |
| 6 | Se una traduzione è troppo lunga, chiede al modello una versione più corta o riduce il corpo fino al 60% |
| 7 | Salva il PDF ottimizzato e un `*_qa_report.json` con le issue per pagina |

## Requisiti

- Windows (i font di sistema sono risolti da `%WINDIR%\Fonts`; il resto è multipiattaforma)
- Python 3.11+ (`pymupdf`, `pyphen`, `requests`; `customtkinter` per la GUI)
- Una chiave API del provider scelto (o un endpoint locale OpenAI-compatibile)

## Avvio rapido

### Doppio clic (nessuna installazione manuale)

| Sistema | File da aprire |
|---|---|
| **Windows** | `start.cmd` |
| **macOS** | `start.command` |
| **Linux** | `start.sh` |

Al primo avvio il lanciatore crea `.venv` e installa le dipendenze (~80 MB, serve internet),
poi apre la GUI. Gli argomenti sono passati alla CLI: `start.cmd doctor`, `start.cmd translate in.pdf out.pdf`.

### Riga di comando

```powershell
py -m venv .venv; .venv\Scripts\Activate.ps1
pip install -e ".[gui]"          # su server/CI basta `pip install -e .`
$env:PDFBOOK_API_KEY = "..."     # oppure compila .env (mai committarlo)

pdfbook gui                      # interfaccia desktop
pdfbook translate libro.pdf libro-ITALIANO.pdf --pages 1-10
pdfbook qa libro_ITALIANO_qa_report.json   # gate: 0 passa, 1 bloccante
pdfbook report libro_ITALIANO_qa_report.json   # report HTML da leggere
pdfbook doctor                    # configurazione redatta + eventuale report QA
```

Configurazione tramite variabili `PDFBOOK_*` (vedi [`.env.example`](.env.example)).
La chiave API **non viene mai salvata su disco**: vive nella sessione o nell'ambiente.

Guida completa (installazione, primo libro, report, problemi frequenti): [`docs/GUIDA.md`](docs/GUIDA.md).

## Qualità misurata

Su *Agile Estimating and Planning* (365 pagine, 4.207 blocchi): 97,7% dei blocchi entra nelle righe originali, output 2,8 MB contro 7,0 MB della prima versione, testo ricercabile. Dettagli e limiti in [`docs/architecture/08-qualita.md`](docs/architecture/08-qualita.md).

### SLO dichiarati

| Dimensione | Obiettivo | Come si verifica |
|---|---|---|
| Affidabilità | 0 eccezioni non gestite su 500 pagine | `tests/integration/test_stress.py` |
| Ripresa | 0 chiamate al provider dopo `--resume` | stesso test, `test_resume_does_not_call_the_provider_again` |
| Gate QA | `untranslated_unresolved`, `glyph_missing`, `text_missing`, `split_failed` a 0 | `pdfbook qa report.json` |
| Throughput | limitato dal provider, non dal rendering locale | riga di metriche in CLI (pagine/min) |
| Costo | visibile per pagina e per run, con tetto `PDFBOOK_MAX_COST` | `Result.summary`, report HTML |
| Cache | riuso fra run identiche, partizione per provider/modello/lingua/glossario/stile | `pdfbook cache` |

## Struttura del repository

```
src/pdfbook/     codice di produzione, per layer:
  domain/        strutture dati e contratti (Protocol)
  extraction/    PDF → PageLayout        layout/      fitting, sillabazione, segmentazione
  fonts/         risoluzione font         translation/ provider LLM, cache, pipeline
  rendering/     redazione + TextWriter   qa/          report e gate
  app/           job di documento          config/      impostazioni (senza segreti)
  gui/           interfaccia desktop       cli.py       translate / doctor / gui
tools/           modularity_check.py, launch.py (avvio guidato)
start.cmd / start.command / start.sh   lanciatori per Windows / macOS / Linux
tests/           test unitari (272)
docs/            documentazione modulare (indice: docs/architecture/README.md)
legacy/          codice Gen 1 congelato (script storici)
```

Il repository contiene **solo codice e documentazione** (≈0,5 MB): nessun PDF, nessuna
traduzione, nessuna cache. I dati editoriali restano in locale, fuori dal progetto.

## Contribuire

**Prima di aprire un file di codice**, leggi [`AGENTS.md`](AGENTS.md) e [`docs/MODULE_MAP.md`](docs/MODULE_MAP.md): contengono le regole vincolanti (budget dimensionali, confini tra layer, documentazione modulare) e la mappa che dice dove intervenire.

Per sapere **cosa** implementare e in che ordine: [`docs/ROADMAP.md`](docs/ROADMAP.md) (fasi, metriche target, criteri di accettazione).

```powershell
py tools/modularity_check.py          # verifica struttura
py -m unittest discover -s tests -v   # test
py -m ruff check src tests tools      # lint
```

## Sicurezza e dati

- Nessuna chiave nel repository: vedi [`SECURITY.md`](SECURITY.md). **Ruota le chiavi** se hai usato l'app precedente.
- PDF, traduzioni e QA report sono **opere protette**: esclusi da git, uso strettamente personale.

## Licenza

Codice distribuito con licenza **MIT** (vedi [`LICENSE`](LICENSE)).
I libri tradotti, i PDF e i file di traduzione **non** sono coperti da questa licenza:
sono opere protette, restano fuori dal repository e non possono essere ridistribuiti.
