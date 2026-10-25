# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/it/1.1.0/); versioni [SemVer](https://semver.org/lang/it/).

## [0.2.1] — 2025-10-25

### Aggiunto

- **Shaping RTL/CJK** — i blocchi in arabo, ebraico, devanagari, cinese, giapponese e coreano
  possono passare dal motore HTML di PyMuPDF (`insert_htmlbox`) con direzione corretta e
  catena di font Noto; issue `shaped_text`, contatore `shaped`, impostazione `PDFBOOK_SHAPING`.
  **Spento di default**: misurazioni alla mano, il percorso HTML non produce un ToUnicode
  corretto e il testo estratto diventa `?`; resta disponibile per prove sulla resa visiva.
- **Anteprima prima/dopo nella GUI** — testo a fronte per pagina (`gui/preview.py`,
  `preview_window.py`) con copertura dei blocchi tradotti.
- **Drag & drop** del PDF nella GUI con l'extra opzionale `tkinterdnd2`.
- **AppImage** Linux nella release (`packaging/appimage.sh`), con desktop file e icona SVG.
- **Firme**: passi Windows (`signtool`) e macOS (`codesign` + `notarytool` + `stapler`) pronti e
  attivi appena i segreti sono configurati.

### Cambiato

- La release include quattro artefatti (zip Windows, tar.gz macOS/Linux, AppImage).
- `unsupported_script` compare solo con shaping disattivato.

## [0.2.0] — 2025-10-25

Prima release "da strumento valido a strumento premium": la pipeline conserva la tipografia,
regge i libri grandi, misura ciò che produce e dice all'utente cosa fare quando qualcosa non
torna. 693 test, gate di struttura a 0 errori, CI verde.

### Aggiunto

- **Stili inline** — grassetto, corsivo e apici/pedici conservati con un round-trip a
  marcatori (`<b>`, `<i>`, `<sup>`, `<sub>`); se il modello non li restituisce il blocco è
  reso nel font dominante con issue `style_flattened`, senza inventare formattazione.
- **Struttura del testo** — paragraph stitching fra pagine, tabelle riconosciute dalla
  geometria, header/footer per ricorrenza, note a piè di pagina riconosciute ed escluse
  dallo stitching, ordine di lettura a due colonne.
- **Font bundle** — registro OFL (Inter, Source Serif, Noto) e nuovo passo della cascata
  `embedded → bundle → sistema → base-14`; `tools/fetch_fonts.py` scarica i binari con SHA-256.
- **Robustezza operativa** — journal + checkpoint con `--resume`, annullamento cooperativo
  (pulsante GUI, `Ctrl+C`, exit 130), cache con timestamp e potatura (`pdfbook cache --prune`),
  log su file con rotazione, errori con codice e rimedio.
- **OCR** — riconoscimento delle pagine scansionate con messaggio azionabile, adapter
  `ocrmypdf` (strato di testo invisibile su copia temporanea), client VLM compatibile OpenAI
  e parser del formato `<|det|>`, confronto fra due letture OCR.
- **Qualità della traduzione** — profili di stile (`fedele`, `scorrevole`, `accademico`,
  `narrativo`), chunking per frase con ricomposizione, memoria terminologica con glossario
  suggerito, controlli su lunghezze/ripetizioni/lingua, round-trip del testo disegnato.
- **Prodotto** — report HTML leggibile, `pdfbook qa` (exit code), `pdfbook report`,
  metriche di run (pagine/min, token, costo/pagina, cache hit), guida utente,
  packaging CI (wheel/sdist) e workflow di release PyInstaller multi-OS.
- **Riconoscimento scritture** — RTL/CJK identificati e segnalati con `unsupported_script`
  invece di produrre glifi mancanti silenziosi.

### Cambiato

- `TranslationSettings` include lo stile nella partizione di cache; `Span` porta la baseline
  (`origin_y`) per riconoscere apici e pedici.
- `build_plans` applica ordine di lettura, note e tag di stile prima dello stitching.
- La pipeline non contiene più `JobResult` (estratto in `app/job_result.py`).

### Corretto

- Un blocco non viene più reso con il font del primo span (perdita di grassetti/corsivi, §11.6).
- Un blocco molto lungo non finisce più in una richiesta unica: si spezza per frase e, se
  manca un pezzo, la chiave risulta mancante invece di essere troncata in silenzio.
- Il golden test distingue le issue stabili da quelle dipendenti dai font di sistema.

### Sicurezza e licenza

- Nessun segreto nel repository; test automatico sui segreti in CI.
- Codice **MIT**; le distribuzioni includono PyMuPDF (**AGPL-3.0**): vedi `THIRD_PARTY.md` e
  `docs/architecture/13-licenza.md`. Scelta registrata: opzione A.

### Limiti noti

- Shaping RTL/CJK non ancora supportato (manca HarfBuzz + Noto).
- Binari non firmati (SmartScreen/Gatekeeper avvisano); AppImage non ancora prodotta.
- GUI senza anteprima a schermo e drag & drop.

## [0.1.0]

Prototipo iniziale: estrazione, traduzione, rendering vettoriale con conservazione del layout,
QA di base, GUI e CLI. Conservato in `legacy/` come riferimento storico.
