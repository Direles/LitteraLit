# Configurazione, build, distribuzione

> Parte dell'architettura: indice in [`README.md`](README.md). Sezioni 9.
> Regole vincolanti: [`AGENTS.md`](../../AGENTS.md).

---

## 9. Configurazione, build e distribuzione

### 9.1 Configurazione utente (GUI)

- Persistenza su `config.json` accanto all'eseguibile (`SCRIPT_DIR` calcolato da `sys.executable` se frozen, altrimenti `__file__`).
- Migrazione legacy: `api_key` + `provider` singoli → mappa `api_keys[provider]`.
- Cambio provider (`on_provider_change`): salva la chiave del vecchio provider, carica quella del nuovo, aggiorna i modelli dal dizionario `DEFAULT_MODELS`, mostra/nasconde il campo `Base URL` per il provider custom.
- "Test Connessione": recupera **prima** la lista modelli reali, poi testa con quello selezionato (o il primo disponibile), aggiornando il combobox.
- Range pagine opzionale (`Da`/`A`), glossario CSV, lingua target (5 lingue).

### 9.2 Build PyInstaller (`app_gui.spec`)

```python
collect_all('customtkinter')   # datas + binaries + hiddenimports
collect_all('pyphen')          # dizionari di sillabazione come datas
EXE(... name='app_gui', upx=True, console=False, strip=False)
```

- `--onefile` implicito (nessuna COLLECT): un singolo `.exe` da **42,2 MB** che estrae in `%TEMP%\_MEIxxxx` a ogni avvio (lentezza di startup e possibile interferenza con antivirus: da valutare).
- `console=False`: nessuna console visibile → tutti i `print` di diagnostica (`[rebuild_vector]`, `[subset_fonts]`, `[debug]`) sono **invisibili all'utente** in produzione.
- Nessuna firma del codice, nessun versioning delle risorse, nessun installer.

### 9.3 Modalità di esecuzione supportate

| Modalità | Comando | Note |
|---|---|---|
| GUI (sviluppo) | `python "conversione gemini/app_gui.py"` | richiede le dipendenze installate |
| GUI (distribuzione) | `conversione gemini/dist/app_gui.exe` | standalone |
| Test offline renderer vettoriale | `python "conversione gemini/test_vector_run.py"` | estrae 10 pagine, mocka il traduttore con fallback all'originale |
| Test offline renderer raster | `python "conversione gemini/test_run.py"` | usa `rebuild_optimized` (modulo **assente** dal repository → script rotto) |
| Pipeline Gen 1 | `python rebuild_v9.py` (o altra variante) | percorsi assoluti hardcoded su `C:\Users\anton\Desktop\…` |

---
