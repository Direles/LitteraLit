# Sicurezza

## Segreti: regole non negoziabili

- Nessuna chiave API, token o password nel repository (codice, JSON, documentazione, test, log).
- La configurazione locale usa variabili d'ambiente o il keyring di sistema; `.env.example` documenta **solo i nomi**.
- La configurazione dell'app precedente (con le chiavi) **non è più presente** né nel progetto né su disco: è stata eliminata. Resta però valida l'azione di rotazione se le chiavi sono state usate prima della cancellazione.
- Nessuna chiave in URL (`?key=...`): finisce in log, proxy e cronologia. Usare gli header dedicati.

## Azione richiesta subito (rotazione)

L'app precedente conservava le chiavi **Anthropic** e **DeepSeek** in chiaro in un file `config.json`, poi eliminato insieme ai dati editoriali. Se quelle chiavi sono state usate, vanno comunque ruotate: la cancellazione del file non le invalida. Procedura:

1. revocare entrambe le chiavi dal pannello del provider;
2. emetterne di nuove e inserirle solo in `.env` locale o nel keyring;
3. eliminare il file (`config.json`) e il suo contenuto dai backup sincronizzati;
4. verificare che `git status` non mostri file di configurazione.

Nota: se il repository viene inizializzato *dopo* la revoca, la storia git non conterrà mai le chiavi. Se invece esistono già commit con segreti, la storia va riscritta (`git filter-repo`) **prima** del push.

## Contenuti proprietari e copyright

I PDF dei libri, le traduzioni complete (`translations.json`, `translations_cache.json`, `batch_*.json`, `extracted_text.json`) e i QA report contengono **testo di opere protette**. Sono esclusi dal repository (`.gitignore`). La pubblicazione di questi file non è coperta da alcuna licenza del codice.

## Segnalazioni

Aprire una issue privata al maintainer (o un security advisory su GitHub) per vulnerabilità o segreti accidentalmente committati. Non aprire issue pubbliche con dettagli sfruttabili.

## Superficie di rischio nota (stato attuale)

| Rischio | Dove | Stato |
|---|---|---|
| Chiavi API in chiaro su disco | file eliminato (ex `config.json` app precedente) | **ruotare comunque** le chiavi usate |
| Chiave Gemini in query string | `translator.py:159,472` | da sostituire con header |
| Messaggi d'errore con body dell'API | `translator.py` (`RuntimeError`) | da filtrare |
| Esecuzione di codice di terze parti (`trust_remote_code` del modello OCR) | sidecar opzionale | solo in container isolato |
