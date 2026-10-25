# Modulo `qa` — report e quality gate

**File**: `qa/report.py`, `qa/textnorm.py`, `qa/checks_glyphs.py`, `qa/checks_geometry.py`
**Layer**: `qa` — può importare `domain` e `config` (R5). Non importa `rendering`.
**Test**: `tests/unit/test_qa_report.py` (15), `test_textnorm.py` (11), `test_checks_glyphs.py` (11), `test_checks_geometry.py` (13)
**Migrazione**: M10 (report) + P0.5 (controlli)

## Responsabilità

| File | Cosa fa | Cosa NON fa |
|---|---|---|
| `report.py` | formato compatibile, scrittura atomica, `gate()` | non rileva problemi |
| `textnorm.py` | normalizza il testo estratto (NBSP, soft hyphen, punteggiatura) | non corregge il PDF |
| `checks_glyphs.py` | confronta atteso vs reso: glifi tipografici persi, testo mancante | non giudica la qualità della traduzione |
| `checks_geometry.py` | sovrapposizioni tra blocchi e testo fuori pagina | non sposta nulla: misura |

Il modulo **non** rileva problemi per conto proprio nel senso di "decidere cosa fare": produce
`QAIssue`; le decisioni (gate, retry) restano a `gate()` e al chiamante.

## Interfaccia

```python
report_path(pdf_path) -> Path                     # "libro.pdf" → "libro_qa_report.json"
write_report(pdf_path, report, counters=None) -> Path   # atomico, UTF-8, indent 2
parse_report(payload | path) -> QAReport          # accetta anche formati storici
gate(report, kinds=GATE_KINDS) -> list[str]       # [] = output accettabile
GATE_KINDS = (UNTRANSLATED_UNRESOLVED, GLYPH_MISSING, TEXT_MISSING)
```

## Controlli P0.5 (novità)

```python
check_page_glyphs(page, expected_segments, actual_text) -> list[QAIssue]
check_page_geometry(page, runs, *, page_width, page_height) -> list[QAIssue]
normalize(text) / tokens(text) / count_special(text)
```

**Glifi** — confronta i conteggi dei caratteri tipografici (`—`, `–`, `’`, `“`, `”`, `«`, `»`, `…`)
**prima** della normalizzazione, e i token **dopo**: un em-dash sostituito da `·` produce
`glyph_missing`; NBSP e soft hyphen non producono falsi allarmi. Oltre il 30% di parole
mancanti produce `text_missing`.

**Geometria** — costruisce il box di ogni riga (ascendenti 0.8×corpo, discendenti
0.25×corpo) e segnala:

- `text_overlap` quando due righe di **blocchi diversi** si sovrappongono per almeno 2 pt
  verticali e il 25% dell'area della più piccola;
- `clipped` quando una riga esce dalla pagina oltre 2 pt.

## Verifica del glossario (Fase 5.1)

```python
check_glossary(page, originals, translations, glossary) -> list[QAIssue]
contains_term(text, term) -> bool        # case/space-insensitive, nessun fuzzy
```

Per ogni unità: se un termine del glossario compare nell'originale e **non** compare nella
traduzione, si registra `glossary_violation` con il termine mancante. È una issue
**informativa**: il glossario è un vincolo di stile, non un errore bloccante; il gate resta
sui difetti che perdono contenuto.

Nessuna dipendenza aggiunta: un falso positivo qui costa più di un falso negativo, quindi
niente fuzzy matching.

## Qualità del testo (Fase 5.4)

```python
check_length_ratio(page, originali, traduzioni) -> list[QAIssue]
check_repetitions(page, traduzioni) -> list[QAIssue]
check_language(page, traduzioni, expected="it") -> list[QAIssue]
run_text_checks(page, originali, traduzioni, expected_lang=...) -> list[QAIssue]
```

| Controllo | Segnale | Soglia |
|---|---|---|
| `length_ratio` | traduzione molto più corta/lunga dell'originale | 0,45 – 2,4 su unità ≥ 40 caratteri |
| `repetition` | stesso shingle di 7 parole ripetuto | ≥ 3 volte, max 3 issue per pagina |
| `wrong_language` | lingua dominante diversa da quella attesa | richiede ≥ 20 parole |

Tutte e tre sono **informative** e non entrano nel gate. La lingua si riconosce con un
punteggio di stopword per `it/en/fr/de/es` (nessuna dipendenza): se la lingua attesa non è
fra queste, o se il punteggio non è strettamente maggiore, non si segnala nulla. Le soglie
sono larghe di proposito: l'italiano è più lungo dell'inglese e i dialoghi hanno frasi
cortissime.

## Verifica sui difetti noti del progetto

| Caso | Risultato |
|---|---|
| `Patton-ITALIANO4.pdf` p16 (em-dash persi) | `glyph_missing: '—' (U+2014): 4 attesi, 0 resi` → gate **FAIL** |
| `Cohn-ITALIANO2.pdf`, 365 pagine (righe estratte) | **65 `text_overlap`** e **26 `clipped`** |
| Pipeline con canvas che disegna `—` come `·` | `glyph_missing` → gate **FAIL** |
| Output nuovo (M8+M9+M11, 2 pagine) | 0 issue, gate **PASS** (nessun falso positivo) |

## Round-trip del testo e caratteri speciali (Fase 1.5)

```python
roundtrip_ratio(attesi, estratto) -> float            # 1.0 = tutto ritrovato
special_chars(estratto) -> Counter                    # nbsp, soft_hyphen
check_roundtrip(page, attesi, estratto) -> list[QAIssue]
```

Dopo ogni pagina si rilegge ci\xf2 che \xe8 stato appena scritto e lo si confronta con i testi
tradotti: se manca pi\xf9 dello 0,1% dei caratteri si registra `roundtrip_loss`; se compaiono
pi\xf9 di 3 NBSP/soft hyphen (difetto §11.7/1 di PyMuPDF) si registra `special_char_leak`.
Entrambe sono **informative**: il gate resta sui quattro difetti che perdono contenuto.

La verifica ha gi\xe0 trovato il difetto sul libro sintetico dei golden (`special_char_leak: 2`):
la riscrittura del CMap ToUnicode con `fontTools` resta un intervento opzionale, ora che il
difetto \xe8 misurato a ogni run invece che scoperto a mano.

## Controllo visivo (Fase 0)

```python
snapshot = canvas.snapshot(dpi=72)          # prima della redazione
... render_page ...
snapshot_dopo = canvas.snapshot(dpi=72)
check_page_visual(page, before, after, text_boxes=...)
```

Due metriche complementari, perché un confronto pixel-per-pixel originale→tradotto **non** ha
senso quando cambia la lingua:

| Metrica | Cosa misura | Soglia |
|---|---|---|
| **SSIM mascherato** | fedeltà di immagini e grafica: si confrontano solo i pixel **fuori** dalle aree di testo (box originali + run effettivamente disegnati) | ≥ 0,98 |
| **mappa dell'inchiostro** (4×4 riquadri) | dove c'era testo e non c'è più → `text_missing`; dove non c'era e ora c'è, e non è area di testo → `visual_drift` | — |

Costo: 2 render a 72 DPI per pagina (~10-20 ms), disattivabile con `PDFBOOK_VISUAL_QA=0`.
`visual_drift` è **informativa**, non bloccante: diventerà bloccante dopo la Fase 1, quando
esisteranno baseline sui libri reali.

## Formato prodotto

```json
{
  "pages": [
    {"page": 2, "issues": [
      {"page": 2, "type": "font_reduced", "block": "b1", "detail": "9.0pt -> 7.0pt"}
    ]}
  ],
  "summary": {"font_reduced": 1, "overflow_shifted": 3}
}
```

Compatibilità verificata sui report reali della Gen 2: `parse_report` accetta
`block: "multiple"` (stringa) e `block: 4` (numero), ignora tipi sconosciuti e non
fallisce su file corrotti o mancanti (restituisce un report vuoto e logga).

### HTML per la revisione (Fase 6.2)

```bash
pdfbook report libro_qa_report.json          # → libro_qa_report_qa_report.html
pdfbook qa libro_qa_report.json              # gate: exit 0 se passa, 1 se bloccante
```

`html_from_report` produce un file **statico** (CSS incorporato, nessun JS, nessuna CDN): si
apre offline e si può allegare. Le issue bloccanti sono evidenziate in rosso, i dettagli sono
sempre escapati (un `<script>` nel testo tradotto non diventa markup).

## Perché il gate è nel modulo

Un report che nessuno legge non è QA. `gate()` rende il report **azionabile**:

| Condizione | Perché blocca |
|---|---|
| `untranslated_unresolved` | testo inglese pubblicato: difetto §11.2/3 |
| `glyph_missing` | caratteri sostituiti o persi: difetto §11.2/13 (em-dash → `·`) |
| `text_missing` | blocchi previsti e non resi: perdita di contenuto |
| `split_failed` | paragrafo a cavallo di pagina non divisibile: la continuazione resterebbe non tradotta |

Le altre issue (`font_reduced`, `retranslated`, `overflow_shifted`) restano **informative**:
sono compromessi accettabili, non errori.

## Invarianti

1. Scrittura **atomica** (`*.tmp` + `os.replace`): un crash non lascia report troncati.
2. `write_report` **non** sovrascrive i contatori delle issue con `counters`: i secondi si
   fondono e vincono i primi solo sulle chiavi assenti.
3. `parse_report` è **totale**: qualunque input produce un `QAReport` (eventualmente vuoto).
4. `gate` non modifica il report e non ha effetti collaterali.
5. I controlli **non giudicano il testo tradotto**: verificano solo che ciò che doveva
   comparire sia comparso. Un errore di traduzione è invisibile qui, per definizione.
6. La normalizzazione è **conservativa**: non tocca lettere o accenti, solo caratteri
   invisibili e punteggiatura tipografica.

## Cosa NON fa e dove andrà

- **Rendering delle issue nella GUI**: `gui/` (M11) consuma `gate()` e il report.
- **Normalizzazione in scrittura** (CMap custom per evitare NBSP nel PDF): non è un problema
  di QA ma di `rendering/`; oggi è mitigato in lettura.
- **Storico delle run / confronto tra versioni**: non previsto; se serve, sarà un modulo
  separato (non gonfiare questo).

## Note per chi modifica

1. Aggiungere un `IssueKind` richiede: enum in `domain/models.py`, eventuale voce in
   `GATE_KINDS`, un test qui e la documentazione in `docs/architecture/09-difetti.md`.
2. Non cambiare le chiavi JSON (`pages`, `summary`, `type`, `block`, `detail`): sono
   consumate dagli strumenti esistenti.
