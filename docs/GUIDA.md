# Guida utente — LitteraLit

Tradurre un libro PDF senza perdere l'impaginazione: il testo italiano prende il posto di
quello inglese, con lo stesso font, lo stesso corpo, le stesse righe. Questa guida copre
installazione, primo libro, configurazione, lettura del report QA e problemi frequenti.

---

## 1. Installazione

Serve **Python 3.11+** (testato su 3.14).

```bash
git clone https://github.com/Direles/LitteraLit.git
cd LitteraLit
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[gui]"
```

Senza `git`: scarica lo ZIP da GitHub ed esegui gli stessi comandi nella cartella scompattata.

### Doppio clic (nessun terminale)

| Sistema | File |
|---|---|
| Windows | `start.cmd` |
| macOS | `start.command` |
| Linux | `start.sh` |

Il lanciatore crea l'ambiente la prima volta e apre l'interfaccia grafica.

---

## 2. Primo libro in cinque minuti

1. Copia `.env.example` in `.env`.
2. Compila almeno `PDFBOOK_API_KEY` e `PDFBOOK_MODEL` (vedi §3).
3. Avvia la GUI (`start.cmd` oppure `pdfbook gui`).
4. Trascina il PDF, scegli il file di uscita, premi **Traduci**.
5. A fine lavoro trovi accanto al PDF:
   - il libro tradotto (`libro_IT.pdf`);
   - il report QA (`libro_IT_qa_report.json`).

Da terminale, lo stesso lavoro:

```bash
pdfbook translate libro.pdf libro_IT.pdf --pages 1-20
```

`--pages` è comodo per un assaggio: traduce solo l'intervallo indicato.

---

## 3. Configurazione

Tutte le impostazioni vivono in `.env` (mai committare questo file) e si possono
sovrascrivere da riga di comando.

| Variabile | Significato | Default |
|---|---|---|
| `PDFBOOK_PROVIDER` | `DeepSeek`, `OpenAI`, `Anthropic`, `Gemini`, `Custom` | — |
| `PDFBOOK_MODEL` | identificatore esatto del modello | — |
| `PDFBOOK_API_KEY` | chiave del provider (mai stampata nei log) | — |
| `PDFBOOK_BASE_URL` | endpoint per provider compatibili OpenAI / LLM locale | — |
| `PDFBOOK_TARGET_LANG` | lingua di arrivo (nome o codice) | `Italiano` |
| `PDFBOOK_GLOSSARY` | termini da lasciare invariati, separati da virgola | vuoto |
| `PDFBOOK_STYLE` | `fedele`, `scorrevole`, `accademico`, `narrativo` | `fedele` |
| `PDFBOOK_WORKERS` | chunk tradotti in parallelo | `1` |
| `PDFBOOK_RATE_LIMIT` | richieste al secondo (0 = nessun limite) | `0` |
| `PDFBOOK_MAX_COST` | tetto di spesa in USD per la run | `0` (nessuno) |
| `PDFBOOK_CACHE_PATH` | translation memory | `~/.cache/pdfbook/tm.json` |
| `PDFBOOK_CHECKPOINT_EVERY` | pagine fra due salvataggi di ripresa | `10` |
| `PDFBOOK_STITCH` | cuce i paragrafi a cavallo di pagina | `1` |
| `PDFBOOK_INLINE_STYLES` | conserva grassetto/corsivo/apici | `1` |
| `PDFBOOK_READING_ORDER` | ricostruisce l'ordine delle pagine a due colonne | `1` |
| `PDFBOOK_VISUAL_QA` | controllo visivo (SSIM mascherato) | `1` |
| `PDFBOOK_OCR` | `auto` usa ocrmypdf sulle scansioni, `off` lo disattiva | `auto` |
| `PDFBOOK_LOG_FILE` | dove scrivere il log (rotazione 2 MB × 3) | cartella di sistema |

### Modello locale (nessun costo, nessuna chiave)

Con LM Studio o Ollama esposti in formato OpenAI:

```dotenv
PDFBOOK_PROVIDER=Custom
PDFBOOK_BASE_URL=http://localhost:1234/v1
PDFBOOK_MODEL=nome-esatto-del-modello
PDFBOOK_API_KEY=
```

La qualità dipende dal modello: sotto i ~7 miliardi di parametri il formato JSON e i tag di
stile tendono a rompersi.

---

## 4. Cosa fa il programma, in ordine

1. **Estrae** i blocchi di testo con font, corpo, colore e baseline.
2. **Riconosce** tabelle, header/footer, note a piè di pagina, colonne e apici.
3. **Cuce** i paragrafi che continuano alla pagina dopo (tradotti una volta sola).
4. **Traduce** in JSON, con glossario, stile e contesto della pagina precedente.
5. **Disegna** il testo italiano nell'area originale, riducendo il corpo se serve.
6. **Controlla** il risultato: glifi, geometria, aspetto visivo, lunghezze, ripetizioni, lingua.
7. **Salva** PDF + report e tiene un journal per riprendere dopo un'interruzione.

---

## 5. Rileggere il report QA

```bash
pdfbook report libro_qa_report.json      # HTML affiancato al report
pdfbook qa libro_qa_report.json          # gate: 0 passa, 1 bloccante
```

Le issue **bloccanti** sono quattro e fermano il gate:

| Tipo | Significato |
|---|---|
| `untranslated_unresolved` | un blocco è rimasto senza traduzione |
| `glyph_missing` | un carattere non è stato disegnato (es. em dash) |
| `text_missing` | una riga non è stata disegnata affatto |
| `split_failed` | un paragrafo a cavallo di pagina non si è potuto dividere |

Tutto il resto è **informativo**: `font_reduced`, `overflow_shifted`, `clipped`,
`paragraph_stitched`, `glossary_violation`, `length_ratio`, `repetition`, `wrong_language`,
`style_flattened`, `scan_page`, `table_misaligned`, `visual_drift`, `unsupported_script`.

Regola pratica: se il gate passa, il libro è pubblicabile; le informative dicono dove
guardare per migliorare la resa.

---

## 6. Riprendere un lavoro interrotto

```bash
pdfbook translate libro.pdf libro_IT.pdf --resume
```

Il journal registra pagina per pagina; la cache contiene le traduzioni già pagate. Alla
ripresa non si richiama il provider per ciò che è già stato fatto (verificato dai test).

**Annullare**: nella GUI c'è il pulsante *Annulla*; da terminale `Ctrl+C`. Il job si ferma a
fine pagina (exit code 130), journal e cache restano: `--resume` riparte da lì senza ripagare
le pagine già tradotte.

Se hai cambiato provider, modello, lingua, glossario o stile, la cache **non** viene riusata:
la chiave include la configurazione.

---

## 7. Manutenzione

```bash
pdfbook cache                            # voci e dimensione
pdfbook cache --prune --max-age 90       # elimina le voci più vecchie di 90 giorni
pdfbook cache --prune --max-entries 200000
```

```bash
pdfbook doctor                            # configurazione + eventuale report
pdfbook doctor libro_qa_report.json       # verifica il gate
```

---

## 8. Problemi frequenti

| Sintomo | Causa probabile | Rimedio |
|---|---|---|
| «Il PDF non contiene testo: serve un OCR preliminare» | scansione senza strato di testo | `ocrmypdf --language ita+eng in.pdf out.pdf` |
| Molte `wrong_language` | il modello ha risposto in inglese | controlla `PDFBOOK_TARGET_LANG` e il modello |
| Molte `length_ratio` | blocchi vuoti o traduzioni troncate | riduci `PDFBOOK_WORKERS`, riprova con `--resume` |
| Testo che sfora o si accavalla | aree troppo strette per l'italiano | `--overflow-policy shrink`, oppure `PDFBOOK_STYLE=fedele` |
| Grassetti spariti | il modello ha tolto i tag | resta il font dominante, issue `style_flattened`; riprova il blocco |
| `429` ripetuti | rate limit del provider | `PDFBOOK_RATE_LIMIT=1`, `PDFBOOK_WORKERS=1` |
| Costo più alto del previsto | contesto e glossario lunghi | `PDFBOOK_MAX_COST` come tetto, `--pages` per provare |

---

## 9. Limiti noti

- **Font**: se il libro usa un font non installato nel sistema, il renderer usa il
  sostituto più vicino e lo segnala (`system_fonts_used`).
- **Colori**: un blocco con più colori viene reso con quello dello span dominante.
- **Tabelle**: le celle sono riconosciute geometricamente; tabelle senza righe nette
  restano prosa.
- **Scansioni**: riconosciute e segnalate, ma l'OCR automatico non è ancora incluso.
- **PyMuPDF** è AGPL: la decisione di licenza per la distribuzione commerciale è aperta
  (roadmap 6.5).

---

## 10. Dove guardare nel codice

| Vuoi cambiare… | Apri |
|---|---|
| estrazione dal PDF | `extraction/` |
| riconoscimento di tabelle, note, colonne | `layout/` |
| prompt e provider | `translation/` |
| come si disegna il testo | `rendering/` |
| controlli e report | `qa/` |
| flusso del job | `app/pipeline.py` |

Le mappe complete sono in `docs/MODULE_MAP.md` e `docs/modules/`.
