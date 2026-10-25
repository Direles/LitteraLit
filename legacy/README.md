# legacy — zona congelata

Codice della **Generazione 1** (pipeline batch offline) e script di ispezione storici.

## Regole (R12 in [`AGENTS.md`](../AGENTS.md))

- ❌ nessuna nuova funzionalità;
- ✅ solo bugfix critici, con test, e solo se il codice non è ancora migrato;
- ❌ nessun import da `src/pdfbook/` verso questa cartella;
- ➡️ ogni migrazione **rimuove** il file corrispondente da qui (la zona può solo restringersi).

## Contenuto (53 file)

| Gruppo | File | Note |
|---|---|---|
| Renderer storici | `rebuild_pdf.py`, `rebuild_v2.py … rebuild_v9.py`, `rebuild_pil.py`, `rebuild_hq.py`, `rebuild_final.py`, `rebuild_redact.py` | 13 varianti sperimentali; superate da `rendering/vector_renderer.py` (M9) |
| Autoring traduzioni | `build_and_apply.py`, `translate_batch.py`, `translations_data.py`, `final_translate.py`, `fix_remaining.py` | contengono **dati di traduzione inline** (violazione R3): non replicare. **Non pubblicati**: sono testo del libro. Sono stati **rimossi dal progetto** e archiviati fuori dal repository (`Documents/LitteraLit-archivio/script-con-traduzioni/`) |
| Estrattori | `extract_to_json.py`, `extract_all.py`, `explore_pdf.py`, `check_json.py` | superati da `extraction/pdf_extractor.py` (M8) |
| Batch manager | `create_batch.py`, `create_batch_v2.py`, `pages_needing_translation.py`, `apply_translations.py`, `show_*.py` | il batching è oggi interno a `translation/pipeline.py` (M4) |
| Verificatori | `check_*.py`, `verify_*.py` | euristiche confluiscono in `qa/` (M10) |
| Sonde tecniche | `test_pixmap*.py`, `test_native*.py`, `test_reconstruct.py`, `test_visual.py`, `test_approach.py`, `render_samples.py` | esperimenti su API PyMuPDF/PIL, conservati come documentazione |

## Perché sono qui

I percorsi assoluti sono hardcoded (`C:\Users\anton\Desktop\traduzione libri\…`), quindi gli script continuano a funzionare anche da questa cartella. **Non eseguirli** su nuovi libri: usa l'applicazione in `src/pdfbook/` (CLI/GUI).

## File deliberatamente **non** pubblicati

Cinque script Gen 1 contengono il **testo tradotto del libro dentro il codice** (violazione R3, ma
soprattutto contenuto editoriale protetto). Sono stati **rimossi dal progetto** e archiviati in
`Documents/LitteraLit-archivio/script-con-traduzioni/`: la cartella `legacy/` pubblicata contiene
solo codice privo di testo del libro.
`build_and_apply.py`, `final_translate.py`, `translate_batch.py`, `fix_remaining.py`, `translations_data.py`.

Se cloni il repository, quei file non ci sono: è voluto. Il codice Gen 1 utile alla storia del
progetto (renderer, estrattori, verificatori) è invece presente.

Mappa di migrazione: [`docs/MODULE_MAP.md`](../docs/MODULE_MAP.md) §5.
