# Architettura — indice

Documentazione architetturale del progetto **PDF Book Translator**, divisa per concern.
Ogni file risponde a **una** domanda e resta sotto le 400 righe (regola R8 in [`AGENTS.md`](../AGENTS.md)).

| File | Sezioni | Risponde a |
|---|---|---|
| [`01-contesto.md`](01-contesto.md) | 1–2 | Perché esiste il progetto, obiettivi, vincoli, le due generazioni di pipeline |
| [`02-inventario-stack.md`](02-inventario-stack.md) | 3–4 | Cosa c'è nel repository e con quale tecnologia |
| [`03-architettura-gen2.md`](03-architettura-gen2.md) | 5 | Moduli, responsabilità, thread, stato |
| [`04-pipeline.md`](04-pipeline.md) | 6 | Flusso dati end-to-end in 8 passi, con riferimenti al codice |
| [`05-algoritmi.md`](05-algoritmi.md) | 7 | Cascata font, fitting, sillabazione, feedback layout→LLM, parsing JSON, adapter |
| [`06-modello-dati.md`](06-modello-dati.md) | 8 | Formato di traduzioni, cache, config, QA report |
| [`07-config-build.md`](07-config-build.md) | 9 | Configurazione utente, PyInstaller, modalità di esecuzione |
| [`08-qualita.md`](08-qualita.md) | 10 | Metriche reali sui libri tradotti e misure indipendenti |
| [`09-difetti.md`](09-difetti.md) | 11 | Difetti, rischi, debito tecnico, con posizione nel codice |
| [`10-valutazione-target.md`](10-valutazione-target.md) | 12–13 | Giudizio complessivo e architettura target (roadmap) |
| [`11-unlimited-ocr.md`](11-unlimited-ocr.md) | 14 | Valutazione di un OCR/VLM end-to-end e QA visivo |
| [`12-appendici.md`](12-appendici.md) | 15–17 | Simboli, costanti di taratura, glossario |
| [`13-licenza.md`](13-licenza.md) | 18 | Licenza PyMuPDF (AGPL): opzioni, impatto, decisione richiesta |

**Routing operativo**: per sapere *quale file aprire* non usare questo indice, usa [`docs/MODULE_MAP.md`](../MODULE_MAP.md).
**Stato del codice**: l'architettura qui descritta è quella **osservata** (Gen 1 + Gen 2); il passaggio alla struttura `src/pdfbook/` è pianificato in `MODULE_MAP.md` §5.
**Governance**: [`AGENTS.md`](../../AGENTS.md) definisce le regole vincolanti (budget, layer, documentazione modulare).

## Come si mantiene questa documentazione

1. Un nuovo argomento → **nuovo file** in questa cartella, con voce nell'indice qui sopra e in `MODULE_MAP.md` §6.
2. Una modifica a un comportamento → aggiorna il file della sezione interessata, non tutti.
3. Se un file supera le 400 righe: si divide per concern (R4, R8).
4. Nessuna duplicazione con `docs/modules/*`: qui il *perché* e il *flusso*, là il *contratto del singolo modulo*.
