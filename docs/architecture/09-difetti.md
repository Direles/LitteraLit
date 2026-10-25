# Difetti, rischi, debito tecnico

> Parte dell'architettura: indice in [`README.md`](README.md). Sezioni 11.
> Regole vincolanti: [`AGENTS.md`](../../AGENTS.md).

---

## 11. Difetti, rischi e debito tecnico (analisi puntuale)

### 11.1 Sicurezza — 🔴 critico

1. **API key reali in chiaro** in `conversione gemini/config.json` (Anthropic e DeepSeek). Se il repository è condiviso/sincronizzato, le chiavi vanno considerate compromesse → revoca e rotazione immediate.
2. **Nessuna cifratura**: il file di config è leggibile da qualunque processo utente. Soluzione: variabili d'ambiente, Windows Credential Manager/DPAPI (`win32crypt`), o `keyring`.
3. **Gemini key in query string** (`translator.py:159,472`): finisce in log di proxy, cronologia, eventuali errori riportati; l'header `x-goog-api-key` è preferibile.
4. Nessuna redazione dei payload nei log/messaggi d'errore: `raise RuntimeError(f"Errore API ({provider}): {err_msg}")` può includere frammenti di risposta dell'API.

### 11.2 Correttezza — 🟠 alto

| # | Difetto | Posizione | Effetto |
|---|---|---|---|
| 1 | **`still_untranslated` con scope che "trapela" tra pagine**: è inizializzata dentro il `try` (`:429`); se `translate_batch` di retry solleva eccezione, il `if still_untranslated:` successivo (`:460`) usa il **valore della pagina precedente** | `rebuild_vector.py:417-466` | QA report con conteggi gonfiati e blocchi sbagliati (i 177 "unresolved" del test Patton); potenziale `NameError` alla prima pagina |
| 2 | **Cache senza partizione per provider/modello/lingua/glossario** | `translator.py:46,296` | una traduzione fatta con DeepSeek per "Italiano" viene riusata per un altro provider o per "Spagnolo" → **cache poisoning** silenzioso |
| 3 | **Fallback silenzioso all'originale** quando il LLM omette una chiave (`translated_dict.get(bid, orig_text)`) | `translator.py:368,378` | testo inglese pubblicato senza errore; solo l'euristica stopword lo intercetta |
| 4 | **Risultati falliti vengono messi in cache** (se il modello restituisce l'originale, viene salvato come "traduzione") | `translator.py:368-372` | errore permanente: ai run successivi la cache restituisce l'originale senza riprovare |
| 5 | **Test Connessione cancella il glossario**: `test_connection` ricostruisce `self.config` senza la chiave `glossary` e la salva | `app_gui.py:401-425` | perdita di configurazione utente |
| 6 | **Nessun controllo del bordo pagina** nello shift verticale | `rebuild_vector.py:490-506,674` | testo che finisce oltre il margine inferiore, senza avviso dedicato (solo il contatore generico `overflow_shifted`) |
| 7 | **Nessun chunking del batch**: una pagina intera (o un blocco enorme) in un'unica richiesta; per Anthropic `max_tokens=4000` | `translator.py:265,235` | output troncato → parsing fallito o blocchi mancanti su pagine dense |
| 8 | **`perfect` semanticamente fuorviante** ("layout identico" nel messaggio finale vs "entra nelle righe") | `rebuild_vector.py:190-215,615,722` | metrica di qualità non affidabile per l'utente |
| 9 | **Colore delle righe TOC ignorato**: `text_color` calcolato per riga ma `tw.write_text(page, color=block_color)` usa quello della prima riga | `rebuild_vector.py:538,561-562` | numeri di pagina linkati in blu diventano neri (o viceversa) |
| 10 | **Stile inline perso**: gli spans sono concatenati in `line_texts`; tutto il blocco è reso col font/size/color del **primo** span | `rebuild_vector.py:352,574-578` | grassetti/corsivi/apici interni al paragrafo scompaiono |
| 11 | **Regex TOC troppo permissiva**: `[\.\s_\-]{4,}` cattura anche righe con 4 spazi e numero finale | `rebuild_vector.py:33` | possibile riformattazione errata di righe normali |
| 12 | **`escape_unescaped_quotes` non è un parser**: su JSON con strutture annidate o escape complessi produce valori corrotti | `translator.py:49` | traduzioni troncate/malformate accettate silenziosamente |
| 13 | **Sostituzione silenziosa di caratteri tipografici nel percorso base-14**: con `insert_text`/`insert_textbox` + `fontname='helv'` em-dash/en-dash/apostrofo tipografico diventano `·` o `?` (misurato: 301 em-dash nei dati → 0 nel PDF, 112 `·`) | Gen 1: `rebuild_v8/v9` (`insert_textbox`) e `rebuild_final`; Gen 2: **solo** fallback `insert_text(..., 'helv')` a `rebuild_vector.py:556,669` e `fitz.Font('helv')` come ultima spiaggia in `fonts.py:152` | perdita silenziosa di punteggiatura, non segnalata da alcun contatore; il percorso `TextWriter` + `fitz.Font` reale è immune (§14.3b) |

### 11.3 Robustezza operativa — 🟠 alto

1. **Nessun retry/backoff** su `429`, `5xx`, timeout: un singolo errore di rate limit su una pagina interrompe il libro (l'eccezione risale fino a `on_error`). Con 4.207 blocchi e ~365 richieste, la probabilità di incappare in un 429 è concreta.
2. **Nessun checkpoint/resume**: `doc.save` avviene solo alla fine. Un crash alla pagina 360 di 365 non lascia nulla, a parte la cache (che però è solo testo, non layout). Manca un salvataggio incrementale o un journal per pagina.
3. **Elaborazione sequenziale**: nessun `ThreadPoolExecutor`/`asyncio`, nessun rate limiter per provider, nessuna stima di durata/costo.
4. **Timeout fisso 60 s**: pagine molto dense con modelli "reasoning" possono superarlo.
5. **Nessuna idempotenza dichiarata**: rieseguire sullo stesso output non è supportato (il PDF di output non è un input valido, avendo testo italiano).
6. **`print` come canale diagnostico**: in `console=False` spariscono; nessun file di log, nessun livello, nessun timestamp.
7. **`os.remove`/cleanup assente** dei file temporanei di test (`temp_vector_test.pdf`, `test_output/temp.png`).

### 11.4 Portabilità e ambiente — 🟡 medio

1. **Windows-only by design**: `WIN_FONTS = %WINDIR%\Fonts` (`fonts.py:22`), font Arial/Times/Consola/ARIALN; su macOS/Linux il fallback è `fitz.Font('helv')` (qualità tipografica molto inferiore).
2. **52 file su 53 contengono percorsi assoluti Windows hardcoded** (`C:\Users\anton\Desktop\traduzione libri\…`), per **116 occorrenze** nei file Gen 1; la Gen 2 li ha eliminati correttamente (solo `SCRIPT_DIR` relativo).
3. **Nessuna dichiarazione delle dipendenze** né vincoli di versione: la riproducibilità dipende dalla macchina.
4. **`__pycache__` con bytecode `cpython-314`** committato di fatto nel repository.
5. **Nessun VCS** (`.git` assente): non esiste storia, diff, blame, branch, rollback. La numerazione `rebuild_v2…v9` è il sostituto artigianale del version control.
6. **Nessun `.gitignore`**: PDF da 176 MB, cache da 1,4 MB, `build/` e `dist/` sono tutti "sorgenti".

### 11.5 Duplicazione e manutenibilità — 🟡 medio

- **13 renderer quasi identici** (`rebuild_pdf`, `v2…v9`, `pil`, `hq`, `final`, `redact`): ognuno ristampa lo stesso preambolo (`sys.stdout = io.TextIOWrapper(...)`, path costanti, `pf()`, `to_rgb()`), con differenze di 10–40 righe. Costo di manutenzione altissimo, rischio di correggere il bug nel file sbagliato.
- **4 "traduttori" monolitici** (`build_and_apply.py` 57 KB, `translate_batch.py` 41 KB, `translations_data.py` 46 KB, `final_translate.py` 27 KB) contengono **dizionari di traduzione inline**: il contenuto del libro è dentro il codice, non in un formato dati. Non sono riutilizzabili né verificabili.
- **15 script di ispezione** con logica duplicata (`check_*`, `verify_*`, `show_*`): letture ripetute di PDF e JSON, conteggi di accenti italiani e stopword inglesi — euristiche non consolidate in un unico modulo QA.
- **`test_run.py` importa `rebuild_optimized`**, modulo che **non esiste** nel repository: script non eseguibile, testimonianza di refactoring incompleto.

### 11.6 Funzionalità mancanti rispetto allo stato dell'arte

| Capacità | Stato | Impatto |
|---|---|---|
| OCR per PDF scansionati | ❌ (errore esplicito) | interi libri non gestibili |
| Layout multi-colonna complesso / riviste | ⚠️ parziale (solo righe affiancate sulla stessa baseline) | colonne vere e proprie con testo fluido su più righe non sono modellate |
| Tabelle | ❌ | le celle vengono trattate come blocchi indipendenti, il fitting può disallineare le colonne |
| Note a piè di pagina / apici | ❌ | apici inglobati nel testo del blocco, corpo ridotto al 60% |
| Testo ruotato / pagine landscape miste | ❌ | `TextWriter` non applica rotazioni |
| Lingue RTL / CJK | ❌ | `LANG_TEST_CHARS` copre 5 lingue latine |
| Glossario con traduzione imposta (non solo "non tradurre") | ❌ | solo lista di esclusione |
| Memoria di traduzione per documento esportabile | ❌ | solo cache globale md5 |
| Ripresa/checkpoint | ❌ | run lunghe non interrompibili |
| Costi/token tracking | ❌ | nessuna visibilità economica |
| Revisione umana in-app (post-editing) | ❌ | QA solo ex-post su JSON |

### 11.7 Emerso durante la migrazione (M9/M11)

Difetti scoperti lavorando sulla nuova architettura, non presenti nell'elenco originale.

| # | Difetto | Dove | Stato |
|---|---|---|---|
| 1 | **Spazi estratti come NBSP** (U+00A0) e trattini come **soft hyphen** (U+00AD) quando il testo è disegnato con `fitz.TextWriter` e un TTF: 984 + 537 NBSP su due pagine campione. Copia/incolla e ricerca testuale degradate. | `rendering/fitz_canvas.py` (comportamento di PyMuPDF) | **mitigato in QA** (`qa/textnorm.py` normalizza in lettura, P0.5); resta aperto il miglioramento del CMap in scrittura |
| 2 | **`perfect` contato per colonna** invece che per blocco nei blocchi strutturati: il conteggio risultava 69 su 13 blocchi. | `rendering/structured_painter.py` | **risolto** in M9 (con test) |
| 3 | **Blocchi strutturati senza issue di clipping**: il painter a colonne non registrava gli sforamenti, quindi un indice che sbordava risultava "pulito". | `rendering/structured_painter.py` | **risolto** in M9 (con test) |
| 4 | **Callback GUI con variabile cancellata**: `self.after(0, lambda: self._failed(str(exc)))` — Python cancella `exc` a fine `except`, quindi il messaggio d'errore sarebbe stato un `NameError` al momento del callback. | `gui/app.py` | **risolto** (individuato da `ruff` F821, ora in CI) |
| 5 | **Cache non partizionata** (già noto, §11.2/2) | `translation/cache.py` | **risolto** in M3: chiave = provider+modello+lingua+glossario |

Lezione operativa: tre dei cinque difetti sono stati trovati **dagli strumenti** (test, gate di
struttura, ruff), non leggendo il codice. È l'argomento più forte a favore del gate automatico.

---
