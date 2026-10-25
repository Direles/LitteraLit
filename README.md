# PDF Book Translator

Traduce libri tecnici in PDF **conservando il layout**: redazione vettoriale del testo originale, riuso dei font embedded, sillabazione nella lingua di destinazione, adattamento tipografico con metriche reali e un report QA per pagina.

> **Stato**: migrazione **completata** (M1–M11). Il codice di produzione vive in `src/pdfbook/`,
> diviso in moduli con budget dimensionali e test. La vecchia app in `conversione gemini/` è
> **congelata** in attesa del primo confronto sul campo, il codice Gen 1 è in `legacy/`.

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

```powershell
py -m venv .venv; .venv\Scripts\Activate.ps1
pip install -e ".[gui]"          # su server/CI basta `pip install -e .`
$env:PDFBOOK_API_KEY = "..."     # oppure compila .env (mai committarlo)

pdfbook translate libro.pdf libro-ITALIANO.pdf --pages 1-10
pdfbook doctor                    # configurazione redatta + eventuale report QA
pdfbook-gui                       # interfaccia desktop
```

Configurazione tramite variabili `PDFBOOK_*` (vedi [`.env.example`](.env.example)).
La chiave API **non viene mai salvata su disco**: vive nella sessione o nell'ambiente.

## Qualità misurata

Su *Agile Estimating and Planning* (365 pagine, 4.207 blocchi): 97,7% dei blocchi entra nelle righe originali, output 2,8 MB contro 7,0 MB della prima versione, testo ricercabile. Dettagli e limiti in [`docs/architecture/08-qualita.md`](docs/architecture/08-qualita.md).

## Struttura del repository

```
src/pdfbook/     codice di produzione, per layer:
  domain/        strutture dati e contratti (Protocol)
  extraction/    PDF → PageLayout        layout/      fitting, sillabazione, segmentazione
  fonts/         risoluzione font         translation/ provider LLM, cache, pipeline
  rendering/     redazione + TextWriter   qa/          report e gate
  app/           job di documento          config/      impostazioni (senza segreti)
  gui/           interfaccia desktop       cli.py       translate / doctor
tools/           modularity_check.py (gate di struttura)
tests/           test unitari (272)
docs/            documentazione modulare (indice: docs/architecture/README.md)
conversione gemini/   app precedente (Gen 2), congelata e **non pubblicata** (vedi `.gitignore`)
legacy/          codice Gen 1 congelato (53 file)
```

## Contribuire

**Prima di aprire un file di codice**, leggi [`AGENTS.md`](AGENTS.md) e [`docs/MODULE_MAP.md`](docs/MODULE_MAP.md): contengono le regole vincolanti (budget dimensionali, confini tra layer, documentazione modulare) e la mappa che dice dove intervenire.

```powershell
py tools/modularity_check.py          # verifica struttura
py -m unittest discover -s tests -v   # test
py -m ruff check src tests tools      # lint
```

## Sicurezza e dati

- Nessuna chiave nel repository: vedi [`SECURITY.md`](SECURITY.md). **Ruota le chiavi** se hai usato `conversione gemini/config.json`.
- PDF, traduzioni e QA report sono **opere protette**: esclusi da git, uso strettamente personale.

## Licenza

Codice distribuito con licenza **MIT** (vedi [`LICENSE`](LICENSE)).
I libri tradotti, i PDF e i file di traduzione **non** sono coperti da questa licenza:
sono opere protette, restano fuori dal repository e non possono essere ridistribuiti.
