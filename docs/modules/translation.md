# Modulo `translation` — adapter, memoria, riparazione JSON

**File**: `translation/json_repair.py`, `cache.py`, `prompts.py`, `pipeline.py`, `providers/{base,openai_compatible,gemini,anthropic,registry}.py`
**Layer**: `translation` — può importare `domain` e `config`, più i propri sottomoduli (R5).
**Test**: `tests/unit/test_json_repair.py`, `test_cache.py`, `test_prompts.py`, `test_providers.py`, `test_pipeline.py`, `test_pricing_ratelimit.py`
**Migrazioni**: M1 (parsing), M2 (provider), M3 (cache), M4 (pipeline) — **completate**.

## Responsabilità

| Modulo | Responsabilità | Cosa NON fa |
|---|---|---|
| `json_repair.py` | Risposta grezza → `dict[str, str]` con scala di degradazione deterministica | Non chiama API, non conosce i provider, non decide i retry |
| `cache.py` | TM persistente, partizionata per configurazione, atomica e thread-safe | Non traduce; la potatura è delegata a `cache_prune.py` |
| `cache_prune.py` | Potatura pura della TM per età e numero di voci | Non fa I/O e non conosce la partizione |
| `providers/base.py` | Trasporto HTTP comune: timeout, `ProviderError`, `error_detail`, `post_json` | Nessun retry, nessuna interpretazione del contenuto |
| `providers/openai_compatible.py` | OpenAI, DeepSeek e endpoint custom (protocollo identico) | Non conosce il registry né i nomi commerciali |
| `providers/gemini.py` | `generateContent`, chiave in header | Nessun forcing di JSON lato server (affidato a M1) |
| `providers/anthropic.py` | `/v1/messages`, blocco `text` anche con *thinking* | Nessun forcing di JSON |
| `providers/registry.py` | Nome provider → istanza configurata; endpoint in un solo posto | Nessuna logica di traduzione |
| `prompts.py` | Prompt di traduzione e di compressione, glossario, contesto troncato | Nessuna chiamata di rete |
| `pipeline.py` | Cache → chunking → provider → riparazione, con retry/backoff | Nessun HTTP diretto, nessun fallback silenzioso all'originale |

## `json_repair.py`

### Interfaccia

```python
parse_json_object(raw: str, expected_keys: Iterable[str] | None = None) -> dict[str, str]
strip_code_fence(raw: str) -> str
escape_unescaped_quotes(text: str) -> str
class JsonRepairError(ValueError): raw: str   # primi 2000 caratteri del payload
```

### Scala di degradazione

| Livello | Strategia | Esito |
|---|---|---|
| 1 | `json.loads` diretto | oggetto valido |
| 2 | rimozione code fence (anche non chiuso) + `json.loads` | gestisce ```json …``` |
| 3 | estrazione per chiave (`"k": "…"`) + decodifica del singolo valore | gestisce virgolette non escapate, virgole finali, newline |
| — | nessuna | `JsonRepairError` con `.raw` conservato per il debug |

Dettagli che il codice legacy sbagliava e qui sono coperti da test:

- virgolette **non escapate** dentro il valore (`lui disse "ciao"`);
- graffe e due punti dentro il valore (`usa {"x": 1}`);
- virgola finale e struttura `}` dopo l'ultima chiave;
- chiavi con `-` e `_`, chiavi duplicate, valori numerici (coerced a stringa).

### Invarianti

1. Restituisce **solo stringhe** (o numeri convertiti): i booleani e le strutture annidate sono scartati.
2. Se `expected_keys` è fornito, l'output è un sottoinsieme di quelle chiavi — mai chiavi inventate.
3. Nessun effetto collaterale, nessuno stato globale, nessun `print`: è una funzione pura testabile.

## `cache.py`

### Interfaccia

```python
make_key(text: str, partition: str) -> str          # sha256(versione|partizione|testo)
TranslationCache(path, partition, *, autosave_every=25)
TranslationCache.for_settings(path, settings, **kwargs)
.get(text) / .contains(text) / .put(text, translation) / .put_many({testo: traduzione})
.save() -> bool          # atomico; False se la scrittura fallisce
.entries / .dirty / .stats()                     # stats include bytes
.prune(max_entries=None, max_age_days=None) -> int
TranslationCache.for_maintenance(path)           # solo prune/stats, senza partizione
```

### Perché la chiave è composta (correzione del difetto §11.2/2)

La Gen 2 usava `md5(testo)`; una traduzione fatta con DeepSeek in italiano veniva riusata
anche per un altro provider, un altro modello o un'altra lingua. Ora la chiave è:

```
sha256( CACHE_VERSION | partition | text.strip() )
partition = TranslationSettings.cache_partition()   # provider|model|target_lang|glossary
```

Conseguenza pratica: **le voci della vecchia cache non sono riutilizzabili** (l'hash non
contiene l'informazione necessaria a ricostruire la partizione). È accettato: erano
potenzialmente avvelenate.

### Garanzie

| Proprietà | Come |
|---|---|
| Atomicità | scrittura su `*.tmp` nella stessa directory + `os.replace` |
| Thread-safety | `threading.RLock` su get/put/save/stats |
| Robustezza | file corrotto o con valori non stringa → warning + ripartenza pulita |
| Nessuna perdita silenziosa | `save()` restituisce `False` e logga l'errore di I/O |
| Nessun segreto nei log | si loggano solo percorsi e messaggi d'errore |

### Formato delle voci e potatura (Fase 3.5)

Ogni voce è ``{"v": traduzione, "t": epoch}``. Il formato legacy (valore stringa) resta
leggibile: ``t = 0`` significa "data sconosciuta", quindi la voce non scade per età ma è la
prima a cadere quando serve spazio.

```python
prune(entries, max_entries=None, max_age_days=None, now=None) -> (tenute, rimosse)
```

`TranslationCache.prune` applica la funzione, riscrive il file solo se qualcosa è cambiato e
restituisce il numero di voci rimosse. Da CLI:

```bash
pdfbook cache                       # statistiche: voci, dimensione
pdfbook cache --prune --max-age 90 --max-entries 200000
```

## `ratelimit.py` e `Completion` (Fase 3.2/3.3)

```python
RateLimiter.from_rate(requests_per_second)     # 0 = nessun limite
limiter.wait()                                  # intervallo minimo, thread-safe

Completion(text, tokens_in, tokens_out)         # risposta del provider
```

- **Token**: ogni adapter estrae `usage` (OpenAI/DeepSeek), `usageMetadata` (Gemini),
  `usage` (Anthropic). Se il provider non li dichiara restano 0: il costo viene omesso,
  non inventato.
- **`Retry-After`**: `post_json` legge l'header e lo espone su `ProviderError.retry_after`;
  la pipeline aspetta `max(backoff^n, retry_after)` invece di martellare il provider.
- **Parallelismo**: `workers > 1` traduce i *chunk* della stessa pagina in parallelo
  (`ThreadPoolExecutor`). Non parallelizza le pagine: lo stitching crea una dipendenza fra
  pagina N e N+1, e romperla sarebbe peggio che andare lenti.
- **Rate limiter** condiviso fra i thread: meglio rallentare che collezionare 429.

## Profili di stile (Fase 5.5)

```python
resolve("accademico") -> StyleProfile          # ValueError se sconosciuto
style_rule(profile, number=7) -> str           # "" per il profilo di default
build_translation_prompt(..., style="narrativo")
```

| Profilo | Registro | Cosa cambia |
|---|---|---|
| `fedele` (default) | neutro | niente: prompt storico, nessuna regola extra |
| `scorrevole` | naturale | preferisce frasi leggibili ai calchi, niente aggiunte |
| `accademico` | formale | mantiene hedging e citazioni intatte |
| `narrativo` | letterario | difende voce e ritmo dell'autore |

Lo stile è **una riga di prompt**, numerata dopo glossario e prima del contesto, e entra
nella partizione di cache (`setting.style`): due stili diversi non condividono traduzioni.
Un nome sconosciuto è un errore di configurazione (exit code 2), non un fallback silenzioso —
così `PDFBOOK_STYLE=accademicoo` si vede subito.

## Esempio d'uso

```python
from pathlib import Path
from pdfbook.domain.models import TranslationSettings
from pdfbook.translation import TranslationCache, parse_json_object
from pdfbook.translation.pipeline import TranslationPipeline
from pdfbook.translation.providers import create_provider

settings = TranslationSettings(provider="DeepSeek", model="deepseek-chat").with_glossary(["Sprint"])
cache = TranslationCache.for_settings(Path.home() / ".cache/pdfbook/tm.json", settings)
pipeline = TranslationPipeline(
    provider=create_provider(settings, api_key=api_key),
    cache=cache,
    settings=settings,
)
outcome = pipeline.translate(batch, context=previous_page_text)
for key in outcome.missing:          # mai sostituiti in silenzio
    report.add(QAIssue(page=page, kind=IssueKind.UNTRANSLATED_UNRESOLVED, block=key))
cache.save()

short = pipeline.shorten(original_text, outcome.translations[key], max_chars=120)
```

## Cosa NON fa e dove andrà

- **Nessun renderer né layout**: `rendering/` e `layout/` consumano l'output della pipeline, non il contrario (R5).
- **Nessuna selezione automatica del provider**: la configurazione arriva da `config/settings.py` (M11).
- **Nessun retry "intelligente" sui contenuti** (rilevamento di blocchi non tradotti): è un controllo di qualità, va in `qa/` (P0.5), non nella pipeline.
- **Nessun pruning/TTL della cache**: da valutare con il tracking dei costi (P4).

## Note per chi modifica questi moduli

1. Aggiungere un test per **ogni** nuovo caso di JSON malformato (M1) e per **ogni** nuovo provider (M2).
2. Non cambiare `CACHE_VERSION` senza una nota di migrazione: invalida tutte le memorie esistenti.
3. I provider non fanno retry: se un test "retry" passa per un provider, l'architettura è stata violata.
4. `pipeline.translate` non deve **mai** restituire una traduzione che non ha ottenuto: usare `TranslationOutcome.missing`.
