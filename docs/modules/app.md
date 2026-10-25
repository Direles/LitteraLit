# Moduli `app`, `config`, `cli`, `gui` — orchestrazione e interfacce

**File**: `app/runtime.py`, `app/pipeline.py`, `config/settings.py`, `cli.py`, `gui/app.py`, `gui/config_panel.py`
**Layer**: `app` (può importare tutti i layer di dominio); `gui`/`cli` possono importare anche `app`.
**Test**: `tests/unit/test_settings.py` (15), `test_app_pipeline.py` (13), `test_cli.py` (8)

I quattro moduli sono documentati insieme perché sono **sottili per costruzione**: nessuno
contiene logica di dominio, tutti compongono ciò che esiste sotto.

## `app/runtime.py` — composizione delle dipendenze

```python
Runtime(source, provider, cache, resolver, canvas_factory, save, close, stats)
build_runtime(input_pdf, settings) -> Runtime
```

È l'unico punto in cui si incontrano PyMuPDF, provider HTTP, cache e font. Nei test si
sostituisce l'intero `Runtime` (vedi `tests/unit/fakes.py`), quindi la pipeline non ha
bisogno di monkeypatch.

`build_runtime` salva su un file temporaneo e poi fa `os.replace`: una run interrotta non
lascia un PDF troncato al posto di quello buono (il difetto "nessun checkpoint" resta
aperto per il *contenuto*, non per l'integrità del file).

## `app/pipeline.py` — il job

```python
JobSpec(input_pdf, output_pdf, settings, page_start=None, page_end=None,
        missing_policy="skip", overflow_policy="keep_size")
TranslationJob(spec, runtime, sleep=time.sleep).run(progress=None) -> JobResult
JobResult(output_pdf, report_path, report, pages, blocks, summary).violations()

batch_for_page(page) -> {chiave: testo}      # b{i} per prosa, b{i}_l{j} per colonne
```

Flusso per pagina: `source.page(i)` → `batch_for_page` → `TranslationPipeline` (cache,
chunking, retry) → `VectorRenderer` (fit, allineamento, disegno) → issue nel report.
Il contesto della pagina precedente è passato alle prime 1500 battute del testo originale.

`JobResult.violations()` è il gate: se contiene qualcosa, l'output **non è pubblicabile**.
CLI e GUI lo usano come esito, non come dettaglio.

## `config/settings.py` — impostazioni

```python
AppSettings(provider, model, target_lang, base_url, glossary, cache_path, log_level, ocr_url, api_key)
load_settings(env=None, env_file=None) -> AppSettings
AppSettings.translation_settings() -> TranslationSettings
AppSettings.missing_required() -> tuple[str, ...]
AppSettings.redacted() -> dict          # la chiave diventa has_api_key: bool
```

- variabili `PDFBOOK_*` (vedi `.env.example`); un `.env` opzionale fa da base e l'ambiente vince;
- `api_key` ha `repr=False`: non compare in log, traceback o `repr(settings)`;
- `missing_required()` è l'unica regola su cosa serve per partire (chiave per i provider
  noti, `base_url` per l'endpoint custom).

## `cli.py` — automazione

```
pdfbook translate in.pdf out.pdf [--provider ...] [--model ...] [--lang ...]
                 [--glossary "Sprint, backlog"] [--pages 1-10]
                 [--cache PATH] [--missing-policy skip|keep] [--overflow-policy ...]
pdfbook doctor [report.json]
pdfbook --version
```

Exit code: `0` successo/gate superato, `1` gate fallito, `2` configurazione incompleta.
`doctor` stampa la configurazione redatta (mai la chiave) e, se riceve un report, ne
verifica il gate — è il comando da usare in CI.

## `gui/app.py` + `gui/config_panel.py` — interfaccia desktop

- Configurazione a sinistra (provider, chiave, modello, base URL, lingua, glossario),
  file e log a destra.
- La traduzione gira in un thread **daemon**; la UI è aggiornata solo con `self.after`.
- La chiave **non viene salvata**: vive nella sessione. Non esiste più un `config.json`
  con credenziali (difetto §11.1/1).
- `import pdfbook.gui` non richiede `customtkinter`: serve solo `pdfbook.gui.app`.

## Cosa NON fanno

- Nessuna logica di traduzione, fitting o disegno (vivono nei rispettivi layer).
- Nessun salvataggio di segreti.
- Nessun retry proprio: quello è della pipeline di traduzione.

## Note per chi modifica

1. Se il job deve cambiare *flusso*, si tocca `app/pipeline.py`; se deve cambiare *come si
   costruiscono le dipendenze*, `app/runtime.py`. Non mescolare i due.
2. Ogni nuova impostazione: campo in `AppSettings` + variabile in `.env.example` +
   `redacted()` + un test in `test_settings.py`.
3. La GUI resta sottile: se una funzione serve anche alla CLI, va in `app/`, non in `gui/`.
