# Contesto, obiettivi, sintesi

> Parte dell'architettura: indice in [`README.md`](README.md). Sezioni 1, 2.
> Regole vincolanti: [`AGENTS.md`](../../AGENTS.md).

---

## 1. Sintesi esecutiva

Il progetto è un **sistema di traduzione di libri tecnici in PDF con conservazione del layout**, composto da due generazioni di pipeline nettamente distinte:

| | **Generazione 1 — "batch offline"** | **Generazione 2 — "vector translator" (attuale)** |
|---|---|---|
| Cartella | radice `traduzione libri/` | `conversione gemini/` |
| Input traduzioni | `translations.json` + file `batch_*.json` compilati manualmente/LLM | cache `translations_cache.json` popolata a runtime dall'API |
| Motore LLM | nessuno integrato (traduzioni "incollate" in script Python) | 5 provider integrati (Gemini, OpenAI, DeepSeek, Anthropic, OpenAI-compatible) |
| Renderer | 13 varianti sperimentali (`rebuild_v2…v9`, `rebuild_pil`, `rebuild_hq`, `rebuild_redact`, `rebuild_final`, `rebuild_pdf`) | 1 renderer canonico `rebuild_vector.py` + `fonts.py` |
| Interfaccia | script CLI con percorsi hardcoded | GUI desktop `app_gui.py` + eseguibile `dist/app_gui.exe` |
| Output | PDF rasterizzato o patchato in modo euristico | PDF **vettoriale** con font riutilizzati, sillabazione, QA report |
| Stato | **legacy / storico**, non più evoluto | **stato dell'arte del progetto** |

La Gen 2 è architetturalmente valida e già sopra la media degli strumenti "PDF translate" generici: redazione vettoriale, riuso dei font embedded, metriche reali del font, sillabazione pyphen, ritraduzione automatica quando il testo non entra, rilevamento e retry dei blocchi rimasti in inglese, report QA machine-readable.

I limiti principali non sono algoritmici ma **di ingegnerizzazione del software**: nessun VCS, nessun test, dipendenze non dichiarate, percorsi assoluti hardcoded, segreti in chiaro, assenza di checkpoint/resume, pipeline monolitica con accoppiamento diretto renderer↔traduttore, e alcuni difetti funzionali specifici documentati in §11.

Una valutazione dell'integrazione di un OCR/VLM end-to-end ([baidu/Unlimited-OCR](https://github.com/baidu/Unlimited-OCR)) — come **oracolo di QA** e per i PDF scansionati — è in **§14**.

---


---

## 2. Contesto e obiettivi

**Obiettivo funzionale**: dato un PDF di un libro tecnico in inglese, produrre un PDF in italiano che mantenga impaginazione, immagini, grafica, colori e gerarchia tipografica, con terminologia tecnica coerente (glossario) e qualità di traduzione "da pubblicazione".

**Vincoli impliciti ricostruiti dal codice**:

1. Il PDF deve avere **testo nativo** (niente scansioni): `rebuild_vector.py` solleva esplicitamente errore se non trova blocchi di testo.
2. Ambiente target **Windows** (font di sistema in `%WINDIR%\Fonts`, dialoghi Tk, eseguibile `.exe`).
3. Esecuzione **offline-ish**: nessun server, nessuna infrastruttura; un solo utente, una sola macchina.
4. Budget/qualità: si preferisce **ridurre leggermente il font** o **accorciare la traduzione via LLM** piuttosto che sbordare o sovrapporre testo.

**Non-obiettivi dichiarati (di fatto)**: collaborazione multi-utente, elaborazione server-side, OCR, lingue RTL, PDF con layout a colonne complesse o rotazioni.

---
