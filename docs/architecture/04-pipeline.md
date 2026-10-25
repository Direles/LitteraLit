# Pipeline end-to-end

> Parte dell'architettura: indice in [`README.md`](README.md). Sezioni 6.
> Regole vincolanti: [`AGENTS.md`](../../AGENTS.md).

---

## 6. Pipeline di Gen 2 — flusso dati end-to-end

### 6.1 Sequenza completa di `process_pdf_vector` (`rebuild_vector.py:283`)

```mermaid
flowchart TD
    A[open PDF] --> B[FontManager: estrazione font embedded<br/>da tutte le pagine]
    B --> C{per ogni pagina nel range}
    C --> D[get_text dict → blocks]
    D --> E[image_boxes = bbox dei blocchi non-testo]
    E --> F[per ogni blocco testo:<br/>righe/spans, testo completo]
    F --> G{blocco strutturato?<br/>righe affiancate o TOC}
    G -->|sì| H[chiavi per riga: b{i}_l{j}]
    G -->|no| I[chiave per blocco: b{i}]
    H --> J[translate_batch con contesto pagina precedente]
    I --> J
    J --> K[euristica: blocchi rimasti in inglese]
    K -->|sospetti| L[retry singolo bypass cache]
    K --> M
    L --> M[add_redact_annot su ogni bbox testo]
    M --> N[apply_redactions images=0 graphics=0 text=0]
    N --> O[ordina blocchi per y]
    O --> P{per ogni blocco}
    P --> Q[blocco TOC → rendering riga/colonna]
    P --> R[blocco prosa → fit_font + wrap + baseline]
    Q --> S[TextWriter.write_text]
    R --> S
    S --> T[shift verticale cumulativo sui blocchi successivi]
    T --> P
    P --> U[subset_fonts]
    U --> V[doc.save deflate=True garbage=3]
    V --> W[scrive <out>_qa_report.json]
```

### 6.2 Passo 1 — Estrazione e segmentazione

- `page.get_text('dict')` fornisce `blocks[]`, ciascuno con `type` (0 = testo, 1 = immagine) e `bbox`.
- Le **immagini** non vengono toccate: le loro bbox alimentano `image_boxes`, usate come ostacolo nel fitting (nessun testo tradotto sopra un'immagine).
- Le righe vuote vengono scartate; il testo del blocco è la concatenazione delle righe (`"\n".join`), **appiattendo gli spans** (vedi §11.2, punto 10: si perde il bold inline).
- **Rilevamento blocchi strutturati** (`rebuild_vector.py:366-384`):
  - `_group_rows()` raggruppa le righe con `origin_y` entro **2 pt** (`ROW_Y_TOLERANCE`) → stima di righe multi-colonna (es. `"Chapter 18:"` + titolo sulla stessa baseline);
  - `_is_toc_line()` riconosce con regex `^(.+?)([\.\s_\-]{4,})\s*([ivxlcdm]+|\d+)$` le righe d'indice con dot-leader;
  - se esiste almeno una riga multi-colonna **oppure** almeno metà delle righe sono "TOC-like", il blocco è trattato riga per riga.
- Chiave di traduzione: `b{idx}` per prosa, `b{idx}_l{li}` per blocchi strutturati.

### 6.3 Passo 2 — Traduzione (con contesto incrementale)

`translate_batch` (`translator.py:265`) riceve `{id: testo}` e restituisce `{id: traduzione}`.

Caratteristiche notevoli:

1. **Batching per pagina**: un'unica richiesta LLM per tutti i blocchi della pagina (riduce costo e mantiene coerenza intra-pagina).
2. **Contesto inter-pagina**: `prev_page_text` (primi **1500 caratteri** del testo originale della pagina precedente) è iniettato nel prompt come riferimento stilistico. È una forma economica di "sliding context".
3. **Glossario**: lista di termini da lasciare in inglese, iniettata come vincolo vincolante ("MANDATORY GLOSSARY").
4. **Istruzioni di stile**: analisi autonoma del dominio, conservazione del gergo tecnico accettato (User Story, MVP, Sprint, …), tono fluido, output solo JSON, preservazione di bullet `■`, spazi multipli e tab.
5. **Cache hit prima della chiamata**: chiave `md5(testo.strip())` (`translator.py:46`) → evita richieste duplicate tra pagine, capitoli e **libri diversi**.

### 6.4 Passo 3 — Post-processing anti-"non tradotto"

Si tratta della parte più "state of the art" del progetto (`rebuild_vector.py:417-466`):

- `_looks_untranslated(original, translated)` (`rebuild_vector.py:250`) usa una lista di **stopword inglesi** (`the, and, of, is, …`, 57 parole) e calcola `_english_word_ratio`.
  - testo **identico** all'originale → sospetto se ratio > 0.15 o lunghezza > 15 caratteri;
  - testo diverso ma con ratio > 0.25 → traduzione parziale/fallita.
- I blocchi sospetti vengono **ritradotti singolarmente** con `bypass_cache=True` (evita di rileggere il risultato sbagliato dalla cache) e, se recuperati, il risultato viene **ripersistito in cache** con una `load→update→save` (per non sovrascrivere le scritture concorrenti).
- I contatori `untranslated_recovered` / `untranslated_unresolved` finiscono nel QA report e nel messaggio finale.

### 6.5 Passo 4 — Redazione vettoriale

```python
for idx, b, full_text, is_toc_block, lines_info in text_blocks:
    page.add_redact_annot(b['bbox'])
page.apply_redactions(images=0, graphics=0, text=0)
```

Questo è il **cuore della qualità**: `images=0` (`PDF_REDACT_IMAGE_NONE`) e `graphics=0` (`PDF_REDACT_LINE_ART_NONE`) preservano immagini e grafica vettoriale; `text=0` (`PDF_REDACT_TEXT_REMOVE`) rimuove fisicamente i caratteri originali dal content stream. Rispetto ai renderer Gen 1 che coprivano il testo con rettangoli bianchi, la differenza è sostanziale: **il testo non è più estraibile né ricercabile in inglese** e non restano "fantasmi" sotto la traduzione.

### 6.6 Passo 5 — Composizione tipografica

Due rami distinti.

**(a) Blocchi strutturati / TOC** (`rebuild_vector.py:508-566`)

- Righe raggruppate in righe visive, colonne processate in ordine di `x0`.
- Ogni colonna usa la **propria** `x0` e una larghezza `bx1 - col_x0 - 4` (non quella dell'intero blocco) → evita che un'etichetta corta e un titolo affiancato si sovrappongano.
- Se una colonna va su più righe, viene calcolata `row_extra_height` e le righe successive della stessa riga visiva vengono spostate (`internal_shift`).
- `optimize_toc_line` (`rebuild_vector.py:73`) **ricalcola i puntini di riempimento** in modo che `titolo + dots + numero pagina` occupi esattamente `max_width`, provando `. `, `.`, `_`, `-`, spazio.
- Le linee sono accumulate in un unico `fitz.TextWriter` e scritte con **un solo colore** (quello della prima riga, `rebuild_vector.py:538,561-562`) — vedi §11.2.

**(b) Blocchi di prosa** (`rebuild_vector.py:568-676`)

1. Font dal primo span (`FontManager.get_font`).
2. Dimensione obiettivo = `size` del primo span; colore dal primo span.
3. `fit_font(...)` cerca la dimensione migliore (dettagli in §7.2).
4. Se `font_size < orig_size * 0.75` e il testo è > 40 caratteri → **ritraduzione compressa** via LLM (`translate_shorter`) entro `estimate_max_chars(...)` caratteri, poi nuovo fit.
5. **Allineamento**: per blocchi a riga singola si confronta il centro del blocco col centro pagina (`detect_single_line_block_alignment`); per blocchi multi-riga si confronta **ogni riga originale** col proprio blocco (`detect_line_alignment`), con soglie 95% di larghezza per "left", 5% del blocco per "center"/"right".
6. **Baseline**: se le righe tradotte sono ≤ righe originali, si **riusano le baseline originali** (spaziatura identica al libro); altrimenti si prosegue con `line_height = size * 1.25`.
7. Rendering con `fitz.TextWriter.append(...)` + `write_text(color=...)`; in caso di eccezione, fallback a `page.insert_text(..., fontname='helv')`.
8. `y_end_points = max(by1 + shift, last_baseline + size*0.20)` viene registrato per il calcolo dello shift dei blocchi successivi.

### 6.7 Passo 6 — Shift verticale adattivo

Poiché l'italiano è tipicamente più lungo dell'inglese, un blocco può occupare più righe. Il codice propaga lo **spostamento verso il basso** ai blocchi successivi che si sovrappongono in X:

```python
shift_points = 0.0
for prev in processed_text_blocks:
    if max(bx0, px0) < min(bx1, px1):          # sovrapposizione orizzontale
        shift_points = max(shift_points, prev['y_end_points'] - py1)
y0_active_pts = by0 + shift_points
```

Il meccanismo evita la collisione con il blocco che ha "spinto" verso il basso, ma **non verifica** il bordo inferiore della pagina né la collisione con blocchi non ancora processati che non si sovrappongono in X (§11.2, punto 6).

### 6.8 Passo 7 — Finalizzazione

```python
doc.subset_fonts()                                   # riduce il peso dei font embeddati
doc.save(out_path, deflate=True, garbage=3)          # compressione + pulizia oggetti
```

Su un libro di 365 pagine questo produce un output di **2,8 MB** contro i 7,0 MB della run precedente senza subsetting — l'ottimizzazione è molto efficace.

### 6.9 Passo 8 — QA report

File `<output>_qa_report.json` con struttura:

```json
{
  "pages": [
    { "page": 2, "issues": [
        {"block": 1, "type": "font_reduced", "detail": "9.0pt -> 6.5pt"},
        {"block": 4, "type": "retranslated", "detail": "traduzione accorciata a ~1234 caratteri"},
        {"block": "multiple", "type": "untranslated_recovered", "detail": "3 blocchi ... recuperati al retry"},
        {"block": "multiple", "type": "untranslated_unresolved", "detail": "... ancora non tradotti ..."}
    ]}
  ],
  "summary": {
    "blocks": 4207, "perfect": 4109, "font_reduced": 2043,
    "retranslated": 3, "overflow_shifted": 1094,
    "untranslated_recovered": 0, "untranslated_unresolved": 0,
    "embedded_fonts_reused": 0, "system_fonts_used": 30
  }
}
```

---
