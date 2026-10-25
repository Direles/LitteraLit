# Appendici

> Parte dell'architettura: indice in [`README.md`](README.md). Sezioni 15, 16, 17.
> Regole vincolanti: [`AGENTS.md`](../../AGENTS.md).

---

## 15. Appendice A — Riferimenti al codice

| Simbolo | File:riga | Ruolo |
|---|---|---|
| `TranslatorApp` | `conversione gemini/app_gui.py:39` | GUI, orchestrazione |
| `start_translation` | `app_gui.py:295` | validazione + avvio thread |
| `update_progress_safe` | `app_gui.py:286` | bridge thread→UI |
| `test_connection` / `run_connection_test_thread` | `app_gui.py:401,432` | discovery modelli + smoke test |
| `load_config` / `save_config` | `app_gui.py:22,31` | persistenza (chiavi in chiaro) |
| `process_pdf_vector` | `rebuild_vector.py:283` | orchestratore pipeline |
| `_group_rows` / `_is_toc_line` | `rebuild_vector.py:41,36` | segmentazione layout |
| `optimize_toc_line` | `rebuild_vector.py:73` | ricalcolo dot-leader |
| `_hyphenate_word` / `wrap_text` | `rebuild_vector.py:103,118` | a capo con sillabazione |
| `detect_line_alignment` / `detect_single_line_block_alignment` | `rebuild_vector.py:156,175` | allineamento |
| `fit_font` | `rebuild_vector.py:190-228` | fitting tipografico |
| `_english_word_ratio` / `_looks_untranslated` | `rebuild_vector.py:241,250` | rilevamento non tradotti |
| `estimate_max_chars` | `rebuild_vector.py:272` | budget caratteri per ritraduzione |
| `DEFAULT_MODELS` | `translator.py:14` | fallback modelli |
| `load_cache` / `save_cache` / `get_cache_key` | `translator.py:25,34,46` | translation memory atomica |
| `robust_json_parse` | `translator.py:65` | parsing a 3 livelli |
| `_call_llm` | `translator.py:152` | adapter provider |
| `translate_batch` | `translator.py:265` | batching + cache + prompt |
| `translate_shorter` | `translator.py:382` | compressione su vincolo di spazio |
| `test_api_connection` / `fetch_available_models` | `translator.py:429,464` | diagnostica provider |
| `FontManager` / `get_font` | `fonts.py:50,157` | cascata di risoluzione font |
| `_classify` / `_fuzzy_match` / `_coverage_ok` | `fonts.py:33,100,90` | euristiche font |


---

## 16. Appendice B — Parametri e costanti di taratura

| Costante | Valore | File | Significato |
|---|---|---|---|
| `RETRANSLATE_THRESHOLD` | 0.75 | `rebuild_vector.py:24` | sotto il 75% del corpo originale si chiede una traduzione più corta |
| `MIN_FONT_FRACTION` | 0.60 | `rebuild_vector.py:25` | riduzione massima del font |
| floor font | 6.0 pt | `rebuild_vector.py:199` | dimensione minima assoluta |
| `ROW_Y_TOLERANCE` | 2.0 pt | `rebuild_vector.py:29` | tolleranza per righe affiancate |
| line height | `size * 1.25` | `rebuild_vector.py:206,642` | interlinea |
| contesto pagina precedente | 1500 char | `rebuild_vector.py:408` | coerenza stilometrica |
| timeout HTTP | 60 s | `translator.py:168,210,239` | per chiamata |
| `max_tokens` (Claude) | 4000 | `translator.py:235` | ⚠ possibile troncamento |
| fattore sicurezza char budget | 0.95 | `rebuild_vector.py:280` | margine su `estimate_max_chars` |
| soglia "identico sospetto" | ratio > 0.15 o len > 15 | `rebuild_vector.py:264` | anti-non-tradotto |
| soglia "parziale sospetto" | ratio > 0.25 | `rebuild_vector.py:268` | anti-non-tradotto |
| almeno metà righe TOC | `max(1, len//2)` | `rebuild_vector.py:384` | classificazione blocco strutturato |
| `garbage` / `deflate` | 3 / True | `rebuild_vector.py:694,698` | pulizia e compressione PDF |


---

## 17. Appendice C — Glossario

- **Blocco (block)**: unità di testo restituita da `page.get_text('dict')`; può contenere più righe.
- **Span**: porzione di riga con font/size/color omogenei.
- **Baseline (`origin`)**: coordinata Y della linea di base del testo; riusarla preserva la spaziatura originale.
- **Redaction**: rimozione fisica dei caratteri dal content stream (`add_redact_annot` + `apply_redactions`).
- **TextWriter**: API PyMuPDF per comporre testo con `fitz.Font` arbitrari in un unico stream.
- **TOC line**: riga d'indice con dot-leader e numero di pagina.
- **Dot-leader**: sequenza di punti/spazi che allinea il numero di pagina a destra.
- **Subset font**: sottoinsieme di glifi effettivamente usati, embeddato nel PDF (`doc.subset_fonts()`).
- **Translation memory (TM)**: archivio riutilizzabile delle traduzioni già effettuate (qui: `translations_cache.json`).
- **QA report**: artefatto JSON con contatori e issue per pagina.
- **`perfect`**: nel codice, blocco che entra nel numero di righe originali senza sovrapporsi a immagini (non implica font invariato).

### Termini introdotti nella §14 (valutazione OCR)

- **VLM (Vision-Language Model)**: modello che accetta immagini e produce testo; qui usato come OCR end-to-end.
- **R-SWA (Reference Sliding Window Attention)**: meccanismo di attenzione che mantiene **costante** la KV cache durante la decodifica, abilitando la trascrizione di decine di pagine in un solo forward pass.
- **`<|det|>` (detection marker)**: marcatore dell'output OCR che precede categoria e bbox di un blocco (`<|det|>text [x1,y1,x2,y2]<|/det|>contenuto`).
- **Sidecar**: servizio locale separato dall'app (qui il server OCR su GPU), chiamato via HTTP; non entra nel binario distribuito.
- **CER (Character Error Rate)**: percentuale di caratteri errati rispetto a un riferimento; metrica di qualità dell'estrazione.
- **MAE dei bbox**: errore medio assoluto tra coordinate dei box OCR e quelle degli span PyMuPDF (in punti).
- **IoU (Intersection over Union)**: rapporto tra area di intersezione e area di unione di due box; usato per verificare che il testo OCR cada dove previsto.
- **Glyph-diff**: confronto token-per-token tra testo atteso e testo effettivamente estraibile dal PDF prodotto, per scoprire caratteri persi o sostituiti (es. `—` → `·`).
- **Tofu**: glifo mancante reso come rettangolo vuoto/`?` nel PDF finale.
