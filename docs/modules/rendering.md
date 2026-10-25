# Modulo `rendering` — dal testo tradotto al PDF

**File**: `rendering/canvas.py`, `colors.py`, `runs.py`, `painter.py`, `structured_painter.py`, `vector_renderer.py`, `fitz_canvas.py`
**Layer**: `rendering` — può importare `domain`, `fonts`, `layout`, `qa`; **mai** `translation`, `extraction`, `app` (R5).
**Test**: `tests/unit/test_vector_renderer.py` (14), `tests/unit/test_runs.py` (11)
**Migrazione**: M9

## Responsabilità

| File | Responsabilità | Cosa NON fa |
|---|---|---|
| `canvas.py` | `TextRun` + contratto `PageCanvas` (redigere, disegnare, riportare i fallimenti) | Nessuna implementazione concreta |
| `colors.py` | intero RGB → tupla 0..1 e `#rrggbb` | Nessuna decisione di stile |
| `runs.py` | geometria pura: baseline, x, shift, altezze extra | Nessun fit, nessuno stato |
| `painter.py` | blocco di prosa: fit, ritraduzione compressa, baseline, issue | Non disegna |
| `structured_painter.py` | blocchi a colonne/indice: ogni colonna con la propria x0 | Non disegna |
| `vector_renderer.py` | orchestrazione di pagina: classificazione, redazione, painter, shift, draw | Nessuna aritmetica tipografica |
| `fitz_canvas.py` | unico punto con `fitz`: redaction + `TextWriter` per colore | Nessuna politica (niente fallback base-14) |

## Flusso di una pagina

```
render_page(canvas, page, translations)
├─ classify_block per ogni blocco + ordinamento per y
├─ canvas.redact(bbox) per tutti, poi canvas.apply_redactions()   ← una sola volta
├─ per ogni blocco:
│   ├─ shift = shift_for(bbox, blocchi già piazzati)
│   ├─ painter = structured se is_structured_block(...) altrimenti prose
│   ├─ painted = painter.paint(block, page, translations, shift)
│   ├─ merge di issue e contatori
│   ├─ draw(painted.runs) → righe non disegnate diventano TEXT_MISSING
│   └─ registra (bbox, y_end) per lo shift dei blocchi successivi
└─ PageRenderResult(issues, blocks, perfect, font_reduced, shifted, retranslated, not_drawn)
```

## Regola: nessun fallback silenzioso

| Situazione | Comportamento | Issue |
|---|---|---|
| traduzione assente (`missing_policy="skip"`, default) | blocco non disegnato | `untranslated_unresolved` (bloccante) |
| traduzione assente (`missing_policy="keep"`) | ridisegnato l'originale | `untranslated_unresolved` (bloccante) |
| testo non entra nelle righe | corpo ridotto o sforamento secondo `overflow_policy` | `clipped` |
| corpo ridotto | ridotto fino al 60%/6 pt | `font_reduced` |
| corpo sceso sotto il 75% e `shortener` disponibile | richiesta versione più corta | `retranslated` |
| `canvas.draw` non riesce a disegnare una riga | la riga viene restituita e **non** sostituita con base-14 | `text_missing` (bloccante) |

Il ripiego base-14 è stato **eliminato**: era la causa della sostituzione `—` → `·`
(§14.3b dell'architettura). Meglio una riga mancante e segnalata che punteggiatura corrotta.

## Verifica end-to-end (M8+M9+M11)

Con un provider fittizio che prefissa il testo (`"IT " + originale`) su *Agile Estimating
and Planning*, pagine 16–17 (indice + corpo):

| Metrica | Valore |
|---|---|
| Blocchi / `perfect` / `shifted` | 13 / **13** / 10 |
| Issue | **0** → gate **PASS** |
| PDF prodotto | 2,12 MB |
| Prefisso applicato | 44 + 21 segmenti |
| Em-dash nel PDF | 1 su 1 (conservata) |
| Font | 0 riuso embedded, 3 fallback di sistema, **0 base-14** |

## Limiti noti (misurati)

| Effetto | Evidenza | Conseguenza | Mitigazione |
|---|---|---|---|
| Spazi estratti come **NBSP** (U+00A0) | 984 + 537 occorrenze su 2 pagine | copia/incolla e ricerca testuale degradate, confronti stringa falliscono | normalizzare in lettura (QA, P0.5) |
| Trattini estratti come **soft hyphen** (U+00AD) | 4 occorrenze su p16 | ricerca della parola trattinata fallisce | stessa normalizzazione |
| Testo dentro immagini non tradotto | il renderer non tocca i pixel | copertine/figure restano in inglese | OCR (roadmap §14) |

Nessuno di questi effetti è silenzioso **se** i controlli QA normalizzano il testo: è il
requisito principale di `qa/checks_glyphs.py` (P0.5).

## Note per chi modifica

1. Un painter non disegna: restituisce righe. Se serve il canvas, la logica è nel posto sbagliato.
2. `perfect` è **per blocco**: un blocco strutturato è perfetto solo se tutte le colonne entrano.
3. Non reintrodurre `insert_text(..., 'helv')`: se il disegno fallisce, si restituisce il run.
4. Le soglie (75% per la ritraduzione, 0.5 pt di shift) sono costanti nominate e testate.
