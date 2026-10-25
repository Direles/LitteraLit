# Architettura di Gen 2

> Parte dell'architettura: indice in [`README.md`](README.md). Sezioni 5.
> Regole vincolanti: [`AGENTS.md`](../../AGENTS.md).

---

## 5. Architettura di Gen 2 (prodotto attuale)

### 5.1 Diagramma di contesto

```mermaid
graph LR
    U[Utente<br/>traduttore / editor] -->|PDF + API key + glossario| GUI[app_gui.py<br/>CustomTkinter]
    GUI -->|settings dict| PIPE[rebuild_vector.py<br/>process_pdf_vector]
    PIPE -->|testo per pagina| TR[translator.py]
    TR -->|HTTPS JSON| LLM[(Provider LLM<br/>Gemini/OpenAI/DeepSeek/Claude/custom)]
    TR <-->|md5→traduzione| CACHE[(translations_cache.json)]
    PIPE -->|font| FM[fonts.py<br/>FontManager]
    FM -->|extract_font| PDF[PDF sorgente]
    FM -->|fallback| SYS[(%WINDIR%\\Fonts)]
    PIPE -->|redazione + TextWriter| OUT[PDF tradotto]
    PIPE -->|contatori + issues| QA[PDF_qa_report.json]
    GUI <-->|provider, chiavi, modello, glossario| CFG[(config.json)]
```

### 5.2 Diagramma dei container/moduli

```mermaid
graph TB
    subgraph "Processo unico (desktop)"
        A[app_gui.py<br/>TranslatorApp : CTk]
        B[rebuild_vector.py<br/>process_pdf_vector]
        C[translator.py<br/>translate_batch / _call_llm]
        D[fonts.py<br/>FontManager]
        E[(translations_cache.json)]
        F[(config.json)]
    end
    G[(PDF in ingresso)]
    H[(PDF + QA report in uscita)]
    I[(API LLM remote)]

    A -->|thread daemon| B
    A <--> F
    B --> C
    B --> D
    C <--> E
    C -->|requests.post| I
    G --> B
    B --> H
```

### 5.3 Responsabilità dei moduli

| Modulo | Responsabilità | Dipendenze interne | Dipendenze esterne |
|---|---|---|---|
| `app_gui.py` | Configurazione, validazione input, orchestrazione thread, progress, log, test connessione, persistenza `config.json` | `rebuild_vector.process_pdf_vector`, `translator.DEFAULT_MODELS/test_api_connection/fetch_available_models` | customtkinter, tkinter |
| `rebuild_vector.py` | Estrazione layout, batching per pagina, redazione, fitting tipografico, allineamenti, shift verticale, QA report, salvataggio | `translator.*`, `fonts.FontManager` | PyMuPDF, pyphen |
| `translator.py` | Adapter per 5 provider, prompt engineering, parsing JSON robusto, cache, ritraduzione compressa, test connessione, discovery modelli | — | requests, hashlib |
| `fonts.py` | Estrazione font embedded, matching fuzzy, verifica copertura glifi, fallback di sistema, metriche `text_length` | — | PyMuPDF, filesystem Windows |

**Accoppiamento**: `rebuild_vector` importa funzioni a livello di modulo da `translator` (`from translator import translate_batch, …`) e da `fonts`. Non esiste interfaccia/iniezione: il test offline (`test_vector_run.py`) è costretto a **monkeypatchare** `translator.translate_batch` e `rebuild_vector.translate_batch` per funzionare senza API key. È il segnale classico di assenza di un seam di architettura.

### 5.4 Modello di concorrenza

```mermaid
sequenceDiagram
    participant UI as Thread Tk (mainloop)
    participant W as Worker (daemon thread)
    participant RV as process_pdf_vector
    participant LLM as Provider LLM

    UI->>UI: start_translation() valida campi, salva config
    UI->>UI: disabilita bottoni, svuota log
    UI->>W: threading.Thread(run_thread_job, daemon=True)
    W->>RV: process_pdf_vector(in, out, settings, progress_callback)
    loop per ogni pagina
        RV->>LLM: POST /chat|/generateContent (bloccante, timeout 60s)
        LLM-->>RV: JSON tradotto
        RV->>UI: progress_callback(current,total,msg)
        UI->>UI: self.after(0, aggiorna progress bar + log)
    end
    RV-->>W: qa_report
    W->>UI: self.after(0, on_success | on_error)
    UI->>UI: riabilita bottoni
```

Punti di merito: il thread worker è `daemon`, la UI non viene toccata da thread secondari (tutto passa da `self.after`), il callback di progresso è dichiarato thread-safe (`update_progress_safe`, `app_gui.py:286`).

Punti di debolezza: **nessuna parallelizzazione** delle chiamate LLM (una pagina per volta, sequenziale), nessuna cancellazione (`start_translation` non espone "Annulla"), nessun timeout globale, nessuna politica di retry/backoff, e un errore su una pagina interrompe l'intero documento (§11).

### 5.5 Stato dell'applicazione (macchina a stati implicita)

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Testing: Test Connessione
    Testing --> Idle: esito mostrato (messagebox)
    Idle --> Running: Avvia Traduzione (validazione OK)
    Idle --> Idle: validazione KO (log errore)
    Running --> Done: return di process_pdf_vector
    Running --> Failed: eccezione propagata al worker
    Done --> Idle
    Failed --> Idle
```

Lo stato non è modellato esplicitamente (nessun `enum`, nessun `state` object): è codificato tramite `state="disabled"` dei widget.

---
