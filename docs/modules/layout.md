# Modulo `layout` — fitting tipografico

**File**: `layout/fitter.py`, `layout/hyphenation.py`, `layout/toc.py`, `layout/segmentation.py`, `layout/aligner.py`
**Layer**: `layout` — può importare `domain` e `fonts`; **mai** `rendering` (R5).
**Test**: `tests/unit/test_fitter.py` (16), `test_hyphenation.py` (9), `test_toc.py` (12), `test_segmentation.py` (19), `test_aligner.py` (13)

## Responsabilità

| File | Responsabilità | Cosa NON fa |
|---|---|---|
| `fitter.py` | A capo, sillabazione, scelta del corpo, stima del budget di caratteri | Non conosce font concreti né coordinate di pagina: riceve `measure(text, size)` e `Rect` |
| `hyphenation.py` | Sillabazione per lingua via `pyphen` | Non decide la larghezza: chiede `width_of` |
| `toc.py` | Riconosce le righe d'indice e ricalcola i puntini di riempimento | Non conosce il resto della pagina |
| `segmentation.py` | Righe visive (colonne affiancate), indici, classificazione del blocco | Non disegna e non decide il corpo |
| `aligner.py` | Allineamento `left`/`center`/`right` di righe e blocchi | Non sposta il testo: restituisce solo etichette |

## Paragraph stitching (Fase 2)

```python
detect_continuations(pages) -> list[Continuation]     # ultimo blocco ↔ primo blocco della pagina dopo
merged_text(previous, following, hyphen=...) -> str   # trattino: si unisce senza spazio
split_translation(first, second, translated) -> SplitResult
```

`Continuation.key` vale `p{prev}:{blocco}+p{next}:{blocco}`, quindi è stabile e leggibile nei log.
Le euristiche per unire due blocchi:

| Condizione | Perché |
|---|---|
| ultimo blocco della pagina **senza** punteggiatura terminale (`. ! ? : ; …`, ignorando virgolette finali) | la frase resta aperta |
| primo blocco della pagina dopo che inizia con **minuscola** | segnale forte di continuazione |
| stesso intervallo orizzontale (overlap ≥ 50%, o `x0` entro 24 pt) | evita di unire colonne diverse |
| blocco nella fascia alta della pagina (`y0 < 35%` dell'altezza) | esclude firme e note in fondo |
| blocchi non strutturati e testo ≥ 20 caratteri | esclude indici, titoli e numeri di pagina |

`split_translation` divide la traduzione **in proporzione** ai due testi originali, cercando un
confine di frase entro ±18% dal punto proporzionale e, in mancanza, un confine di parola. Se una
parte scenderebbe sotto il 20% del totale non si divide: `SplitResult.usable` è `False` e il
chiamante registra `split_failed` (bloccante), invece di pubblicare una pagina mezza vuota.

**Costo noto**: il job materializza le pagine dell'intervallo per guardare avanti di una pagina.
Per libri enormi è il primo punto da ottimizzare (streaming a finestra).

## Segmentazione e allineamento (M7)

```python
group_rows(lines, tolerance=2.0) -> list[list[Line]]      # righe visive, colonne ordinate per x
has_multi_column_row(lines) -> bool
toc_ratio(lines) -> float                                  # frazione di righe d'indice
is_structured_block(block) -> bool                          # colonne o indice → rendering riga per riga
classify_block(block) -> TextBlock                          # PARAGRAPH|TITLE|TOC_ROW|LIST_ITEM|CAPTION|UNKNOWN

line_alignment(line, block) -> str
single_line_alignment(block, page_width) -> str
alignments_for(block, page_width, line_count) -> tuple[str, ...]
```

Regole di classificazione, in ordine: indice (`toc_ratio ≥ 0.5`) → titolo (`CAPITOLO`/`Chapter`,
riga corta che finisce con `:`, tutto maiuscolo) → voce di elenco (`■`, `1.`, `a)`) → numero isolato
(`CAPTION`) → `PARAGRAPH`. `classify_block` **non muta** il blocco: restituisce una copia
(`dataclasses.replace`), così il blocco originale resta confrontabile nel QA.

Soglie dell'allineamento: riga piena (≥95% del blocco) → `left`; centro entro
`max(5% del blocco, 5 pt)` → `center`; bordo destro entro la stessa tolleranza → `right`.
Per i blocchi a riga singola il riferimento è il centro pagina (15 pt, blocchi < 80% pagina).

## Interfaccia

```python
wrap_text(text, *, measure, size, max_width, hyphenation=None) -> list[str]
fit_text(text, *, measure, max_width, target_size, max_lines, bounds,
         obstacles=(), hyphenation=None, min_fraction=0.60, min_size=6.0,
         overflow_policy="keep_size") -> FitResult
estimate_max_chars(measure, *, size, max_width, num_lines, sample) -> int

FitResult(size, lines, fits)      # .line_height, .height(), .reduced_compared_to(target)

Hyphenation(target_lang)          # .available, .pairs(word), .split_for_width(word, width_of, available)
is_toc_line(text) -> bool
optimize_toc_line(text, *, measure, max_width) -> str
```

## Algoritmo di `fit_text`

```
floor = max(target * 0.60, 6.0)
size  = target
mentre size >= floor:
    righe = wrap_text(size)
    se non invade ostacoli e righe <= max_lines → FIT (size, righe)
    memorizza il primo tentativo senza invasioni (fallback)
    size -= 0.5
se nessun FIT:
    overflow_policy == "keep_size" → corpo originale, testo sborda, fits=False  (storico)
    overflow_policy == "shrink"    → corpo minimo, invasione ridotta,  fits=False
```

## Perché `overflow_policy` è un parametro

Il comportamento storico (`keep_size`) mantiene leggibile il testo ma è la causa misurata
delle sovrapposizioni (§14.3a: 102 coppie su Cohn, 69 su Patton). `shrink` riduce
l'invasione sacrificando il corpo. Nessuna delle due è "giusta": il renderer deve poter
scegliere e **registrare l'issue**. `fits=False` è l'unico segnale che il chiamante deve
onorare.

## Invarianti

1. `wrap_text` non produce righe più larghe di `max_width`, **tranne** quando una singola
   parola non è sillababile: in quel caso la riga sborda (e il chiamante lo vede da `fits`).
2. Con sillabazione attiva, `"".join(righe).replace("-", "")` ricostruisce il testo originale.
3. `estimate_max_chars` usa un fattore di sicurezza (0.95) e non restituisce mai valori negativi.
4. `optimize_toc_line` è **idempotente** su una riga già ottimizzata e non tocca testo non-TOC.

## Verifica su libro reale

Con le metriche di `MinionPro-Regular` estratto dal PDF Patton: un paragrafo italiano di
~300 caratteri a 9 pt, larghezza 330 pt, massimo 6 righe → `size=9.0`, 3 righe,
`fits=True`, riga più lunga **329,1 pt** (limite 330).

Segmentazione sul PDF Cohn (blocchi costruiti dall'estrazione):

| Pagina | Blocchi | Strutturati | Tipi dedotti |
|---|---|---|---|
| p16 (indice "Contents") | 8 | **8** | 5 `toc_row`, 3 `title` |
| p100 (corpo) | 14 | 0 | 12 `paragraph`, 1 `title` ("Chapter 8"), 1 `caption` (numero pagina) |

Limite noto: il sottotitolo di capitolo ("Choosing between Story Points and Ideal Days")
resta `paragraph` — senza il contesto delle pagine precedenti non esiste un criterio
affidabile. Meglio un falso negativo che un falso positivo che riduce il corpo del testo.

## Cosa NON fa e dove andrà

- **Shift verticale tra blocchi** → è politica di rendering, non di fitting (`rendering/`, M9).
- **Tabelle come entità** (celle legate fra loro): oggi le celle sono blocchi indipendenti; richiede un modulo dedicato.

## Note per chi modifica

1. Ogni nuova soglia (60%, 6 pt, 1.25) va in `layout/` come costante nominata e documentata in
   `docs/architecture/12-appendici.md`, non scritta a mano nel renderer.
2. I test usano una metrica finta (`len * size * 0.5`): se un test ha bisogno di un font vero,
   è un test di integrazione e va in `tests/` con un fixture PDF, non qui.
3. La sillabazione è **opzionale**: non introdurre dipendenze obbligatorie da `pyphen` (R14).
