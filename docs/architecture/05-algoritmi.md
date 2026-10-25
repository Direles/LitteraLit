# Algoritmi caratterizzanti

> Parte dell'architettura: indice in [`README.md`](README.md). Sezioni 7.
> Regole vincolanti: [`AGENTS.md`](../../AGENTS.md).

---

## 7. Algoritmi caratterizzanti

### 7.1 FontManager — strategia a cascata (`fonts.py:50`)

```
get_font(pdf_fontname)
├─ cache hit? → ritorna
├─ 1. font EMBEDDED nel PDF, per nome base (dopo aver rimosso il prefisso subset "ABCDEF+")
│     └─ se assente → _fuzzy_match(): stessa famiglia normalizzata (prefisso prima di "-",
│        con rimozione suffissi "tot"/"ot"/"t"), punteggio su bold/italic/regular/narrow
│     └─ _coverage_ok(): il font deve avere glifo per TUTTI i caratteri test della lingua
│        (accenti italiani, ecc.) → altrimenti scarta
└─ 2. fallback: font di sistema classificato per famiglia
      _classify(): mono se typewriter/courier/mono/ocr/consol
                   serif se minion/times/georgia/garamond/serif/book
                   sans-narrow se condensed/narrow/compressed
                   altrimenti sans
      SYSTEM_FAMILIES: sans→arial, sans-narrow→ARIALN, serif→times, mono→consola
      selezione variante: idx = (2 se italic) + (1 se bold)
      ultima spiaggia: fitz.Font('helv')
```

Valore architetturale: le **metriche sono reali** (`font.text_length`), non stime basate sul rapporto tra lunghezze dei caratteri. È la differenza principale rispetto a tutti i renderer Gen 1, che usavano `calc_scale(len(orig), len(trans))` con coefficienti arbitrari.

Limite: la strategia di riuso dipende da quanto il subset embedded è "generoso". I dati reali lo dimostrano: sul Patton (prodotto con Antenna House, font Guardian) il riuso è efficace (`embedded_fonts_reused: 13`, `system_fonts_used: 2`), mentre sul Cohn (prodotto con Acrobat Distiller, font Type1/subset minimali) il riuso è **nullo** (`embedded_fonts_reused: 0`, `system_fonts_used: 30`) e tutto passa ad Arial.

### 7.2 `fit_font` — fitting tipografico (`rebuild_vector.py:190`)

```
min_size = max(target * 0.60, 6.0)          # MIN_FONT_FRACTION, floor 6pt
size = target
while size >= min_size:
    lines = wrap_text(text, font, size, max_width, hyphenator)
    y_end = y0 + len(lines) * size * 1.25
    overlaps_image = intersezione bbox con image_boxes
    if not overlaps_image and len(lines) <= original_num_lines:
        return size, lines, True             # "perfect"
    if not overlaps_image and best_fallback is None:
        best_fallback = (size, lines)
    size -= 0.5
return best_fallback or (min_size, wrap(min_size), False)
```

Osservazioni:
- ricerca **lineare a passi di 0.5 pt** (al massimo ~40 iterazioni per blocco, accettabile);
- il flag `perfect=True` significa *"entra nel numero di righe originali senza toccare immagini"*, **non** *"font invariato"* — da qui la coesistenza apparentemente contraddittoria di `perfect: 4109` e `font_reduced: 2043` nel report Cohn (§11.2, punto 8);
- il fallback può ridurre il font fino al 60% e comunque sbordare di righe: in quel caso nessun meccanismo impedisce l'invasione del blocco successivo, se non lo shift a valle.

### 7.3 `wrap_text` + sillabazione (`rebuild_vector.py:118`)

- Prima applica `optimize_toc_line` (ricalcolo dot-leader).
- Poi word-wrap con **metriche reali**; se una parola non entra e la riga ha già contenuto, tenta la sillabazione con `pyphen.iterate(word)` scegliendo il prefisso più lungo che entra (`_hyphenate_word`, parole ≥ 6 caratteri).
- Lingue supportate per la sillabazione: `Italiano → it_IT`, `Inglese → en_US`, `Spagnolo → es`, `Francese → fr`, `Tedesco → de_DE`.

Questo è un dettaglio di qualità tipografica raro negli strumenti automatici: la sillabazione in italiano riduce drasticamente i "buchi" e le righe troppo corte.

### 7.4 `translate_shorter` — feedback loop layout↔LLM (`translator.py:382`)

Quando la traduzione non entra (font sceso oltre il 75% dell'originale):

1. `estimate_max_chars` stima i caratteri disponibili: campiona i primi 200 caratteri, calcola la larghezza media per carattere con il font reale, moltiplica per `num_lines` e per un fattore di sicurezza **0.95**;
2. chiede al LLM una riscrittura **entro `max_chars`** preservando il significato;
3. accetta solo se `len(short) < len(current)` e la cache (chiave `"short_" + md5(testo|max_chars)`) per non ripetere la chiamata.

È un **controllo a retroazione** del layout sul testo (layout-driven translation), presente in pochi prodotti commerciali e qui implementato in ~40 righe.

### 7.5 Parsing JSON robusto (`translator.py:65`)

Scala di degradazione a 3 livelli:

1. `json.loads` diretto;
2. rimozione dei code fence markdown (```json … ```);
3. **estrazione regex per chiave**: individua le posizioni di `"key": "` per le chiavi attese, ritaglia il valore fino alla chiave successiva, chiude a mano le virgolette e decodifica con `escape_unescaped_quotes` + `json.loads('"…"')`, con fallback a sostituzioni manuali (`\"`, `\\`, `\n`, `\t`).

In caso di fallimento definitivo, il payload grezzo viene salvato in `debug_failed_response.txt` (attualmente **0 byte**, quindi l'ultima run non ha avuto fallimenti di parsing).

### 7.6 Adapter per provider (`translator.py:152`)

| Provider | Endpoint | Auth | JSON forcing | Note |
|---|---|---|---|---|
| Google Gemini | `…/v1beta/models/{model}:generateContent` | `?key=` in **query string** ⚠ | `generationConfig.responseMimeType=application/json` | validazione `candidates`, `promptFeedback.blockReason` |
| OpenAI | `https://api.openai.com/v1/chat/completions` | Bearer | `response_format={"type":"json_object"}` | |
| DeepSeek | `https://api.deepseek.com/chat/completions` | Bearer | idem | |
| OpenAI-compatible | `{base_url}/chat/completions` | Bearer opzionale | idem | es. Ollama/LM Studio/vLLM |
| Anthropic Claude | `https://api.anthropic.com/v1/messages` | `x-api-key` + `anthropic-version: 2023-06-01` | **nessun forcing** → affidamento a `robust_json_parse` | `max_tokens: 4000`; gestione esplicita di *extended thinking* (cerca il blocco `type=="text"`, non il primo) |

La funzione `fetch_available_models` (`translator.py:464`) implementa la discovery per tutti i provider con fallback a `DEFAULT_MODELS` — scelta corretta, perché i nomi modello invecchiano rapidamente (il commento nel codice lo dice esplicitamente per Anthropic).

---
