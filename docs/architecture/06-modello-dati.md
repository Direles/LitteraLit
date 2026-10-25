# Modello dati

> Parte dell'architettura: indice in [`README.md`](README.md). Sezioni 8.
> Regole vincolanti: [`AGENTS.md`](../../AGENTS.md).

---

## 8. Modello dati

### 8.1 Gen 1 — `translations.json` (2.742 voci)

```json
{
  "p16_b0": {
    "original": "While the idea of collaboration is neither new …",
    "translated": "Sebbene l'idea di collaborazione non sia né nuova …"
  }
}
```

- Chiave: `p{pagina}_b{indice_blocco}` (indice derivato da `page.get_text('dict')` di PyMuPDF).
- Copertura: pagine 1–324, 309 pagine con blocchi testuali (15 pagine senza testo, es. tavole a piena pagina).
- Qualità: **0 voci vuote**, **150 voci identiche all'originale** (termini da non tradurre, numeri, nomi propri, sigle — oppure residui non tradotti).

### 8.2 Gen 1 — lotti `batch_p{start}-{end}[_DONE].json`

```json
{ "p111_b0": { "original": "…", "translated": "…" } }
```

11 lotti (16–35 … 291–324), 2.634 blocchi complessivi, con tasso di traduzione effettiva per lotto:

| Lotto | Blocchi | Tradotti | Note |
|---|---|---|---|
| p16-35 | 175 | 168 | |
| p36-55 | 169 | 168 | |
| p56-80 | 215 | 193 | |
| p83-110 | 205 | 198 | |
| p111-140 | 248 | 241 | |
| p141-170 | 242 | 233 | |
| p171-200 | 214 | 210 | |
| p201-230 | 207 | 192 | |
| p231-260 | 246 | 242 | |
| p261-290 | 238 | 192 | maggior numero di residui |
| p291-324 | 475 | 462 | include l'indice analitico |

### 8.3 Gen 2 — `translations_cache.json` (5.952 voci)

```json
{ "0da774935621aabcfb72c78b534f52a5": "Jeff Patton\ncon Peter Economy\n…" }
```

- Chiave: `md5(text.strip())` — **solo il testo**, nessun provider/modello/lingua/glossario.
- Scrittura **atomica** (`tmp` + `os.replace`) e `indent=2`: robusta rispetto a crash, ma costosa (riscrittura integrale dell'intero file a ogni pagina → ~1,4 MB × 365 pagine).
- Funge di fatto da **unica translation memory** della Gen 2: non esiste export per-documento.

### 8.4 `config.json`

```json
{
  "provider": "<PROVIDER>",
  "api_keys": { "<PROVIDER>": "<API_KEY_REDACTED>" },
  "api_key": "<API_KEY_REDACTED>",
  "model": "<MODEL>",
  "target_lang": "Italiano",
  "custom_base_url": "",
  "glossary": []
}
```

⚠ **Le API key sono salvate in chiaro e sono attualmente presenti nel repository** (chiavi reali Anthropic e DeepSeek). Va considerato un incidente di sicurezza, non solo un debito tecnico (§11.1).

### 8.5 `extracted_text.json` (Gen 1)

Dump completo del PDF Patton: 324 pagine × blocchi con `type`, `bbox`, `text`, `lines[].spans[]` (testo, font, size, color, bbox). 7,2 MB, usato solo per generare i batch e ispezionare il layout; non è input della Gen 2 (che rianalizza il PDF a ogni run).

---
