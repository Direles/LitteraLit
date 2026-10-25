# Modelli locali: LM Studio, Ollama, vLLM

LitteraLit parla con qualsiasi server **compatibile OpenAI**. In locale non serve una chiave:
serve l'endpoint giusto e il nome esatto del modello caricato. Questo documento copre i due
passaggi che di solito bloccano: la configurazione e la scoperta automatica dei modelli.

## 1. LM Studio

1. Apri LM Studio → **Search**: scarica un modello adatto alla traduzione (7B–14B in Q4/Q5
   bastano per un libro; 20B+ se hai VRAM).
2. Scheda **Chat**: carica il modello (deve comparire in alto come *loaded*).
3. Scheda **Server** (icona `</>`): premi **Start Server**. L'endpoint predefinito è
   `http://localhost:1234/v1`.
4. Verifica che risponda: `pdfbook models` (vedi §3).

```dotenv
PDFBOOK_PROVIDER=Custom
PDFBOOK_BASE_URL=http://localhost:1234/v1
PDFBOOK_MODEL=<id esatto mostrato da "pdfbook models">
PDFBOOK_API_KEY=
PDFBOOK_WORKERS=1
PDFBOOK_RATE_LIMIT=0
```

Un solo modello caricato per volta, di norma: il nome cambia ogni volta che ne carichi un
altro, quindi conviene leggere la lista invece di copiarlo a mano.

## 2. Ollama e vLLM

| Server | Endpoint tipico | Note |
|---|---|---|
| Ollama | `http://localhost:11434/v1` | `ollama pull qwen2.5:7b`, poi `ollama serve` |
| vLLM | `http://localhost:8000/v1` | `vllm serve <model>`; supporta più richieste in parallelo |
| llama.cpp | `http://localhost:8080/v1` | `llama-server -m modello.gguf` |

Gli stessi preset sono in `translation/providers/discovery.py` (`LOCAL_PRESETS`).

## 3. Lettura automatica dei modelli caricati

```bash
pdfbook models                       # usa PDFBOOK_BASE_URL o LM Studio
pdfbook models --base-url http://localhost:11434/v1
pdfbook models --json                # {id, owned_by, context}
```

Esempio:

```
Modelli su http://localhost:1234/v1:
  qwen2.5-7b-instruct (32768 token)
```

Se non c'è nessun modello:

```
Nessun modello caricato su http://localhost:1234/v1
In LM Studio: scheda Server → carica un modello → Start Server.
```

Exit code: `0` se la lettura riesce (anche con lista vuota), `4` se il server non risponde.

**Nella GUI**: il pulsante *Leggi modelli caricati* nel pannello di configurazione fa la
stessa cosa e popola la tendina del modello; il campo *Base URL* si precompila con LM Studio
quando scegli `Custom OpenAI-Compatible`.

## 4. Come scegliere il modello

| Cosa guardare | Perché conta |
|---|---|
| **JSON affidabile** | la pipeline chiede un oggetto JSON con le stesse chiavi; modelli piccoli aggiungono testo o rompono le chiavi |
| **Context ≥ 8k** | un chunk è ~6.000 caratteri più contesto e glossario; sotto 4k si rischia il troncamento |
| **Italiano** | modelli addestrati su molto italiano sbagliano meno registro e accordi |
| **Velocità** | un libro di 300 pagine sono centinaia di richieste: 20 token/s sono ~3-4 ore |

Regola pratica: un 7B Q4 è il minimo per provare; un 14B Q5 è il compromesso ragionevole; i
modelli "reasoning" (con `思考`/thinking) tendono a inserire testo extra e vanno evitati o
gestiti con `PDFBOOK_WORKERS=1`.

## 5. Problemi frequenti

| Sintomo | Causa | Rimedio |
|---|---|---|
| `nessun server su http://localhost:1234` | server spento o porta diversa | **Start Server** in LM Studio; controlla la porta nelle impostazioni |
| Lista vuota | nessun modello caricato | carica il modello nella scheda Chat |
| `PDFBOOK_MODEL` non trovato | nome diverso (spesso con quantizzazione) | copia l'id da `pdfbook models` |
| Risposte troncate / JSON rotto | context troppo piccolo | modello con context ≥ 8k, `PDFBOOK_WORKERS=1` |
| Lento | modello grande o GPU assente | modello più piccolo in Q4, oppure provider cloud |
| `401` | endpoint remoto con chiave sbagliata | per i locali la chiave resta vuota |
