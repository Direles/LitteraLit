# AGENTS.md — Regole di ingegneria (vincolanti)

Questo file è **legge** per ogni agente o persona che modifica il repository.
Complementa `~/.pi/agent/AGENTS.md` (stile di esecuzione): quello dice *come rispondere*, questo dice *come strutturare il codice*.

**Principio unico da cui derivano tutte le regole:**
> Il repository è una **mappa**, non un libro. Ogni task deve essere risolvibile aprendo **al massimo 2 file** indicati in [`docs/MODULE_MAP.md`](docs/MODULE_MAP.md), più il test del modulo.

Se per capire cosa toccare devi leggere 5 file, **la struttura è rotta**: fermati e sistemala (R4), non aggirarla.

---

## R0 — Protocollo di routing (obbligatorio, prima di ogni modifica)

1. Apri **solo** `docs/MODULE_MAP.md` e cerca la riga "Se devi…".
2. Identifica il modulo responsabile. Se non esiste → R9.
3. Apri **solo**: il file target, il suo contratto (`src/pdfbook/domain/ports.py` o `models.py`) e il test relativo.
4. Se dopo questi file il quadro è ancora incompleto: **stop**. O aggiorni la mappa (R10) o proponi uno split (R4). Vietato "leggere tutto per capire".
5. Prima di chiudere: `py tools/modularity_check.py` + test del modulo.

Nessuna eccezione a R0. Un task svolto bene produce un diff piccolo in un file prevedibile.

---

## R1 — Budget dimensionali (hard limit)

| Metrica | Target | Errore |
|---|---|---|
| Righe per file di codice | ≤ 300 | > 450 |
| Def/class top-level per file | ≤ 12 | > 16 |
| Righe per funzione/metodo | ≤ 50 | > 80 |
| Righe per documento `.md` in `docs/` | ≤ 400 | > 600 |
| Responsabilità per modulo | 1 | ≥ 2 |

I budget non sono consigli: sono la condizione che rende possibile il routing di R0.

## R2 — Luoghi canonici (nessun file di codice alla radice)

| Zona | Contenuto ammesso |
|---|---|
| radice | solo `README.md`, `AGENTS.md`, `SECURITY.md`, `LICENSE`, `ARCHITETTURA.md`, `pyproject.toml`, `.gitignore`, `.env.example`, i lanciatori `start.cmd`/`start.command`/`start.sh`, stub di reindirizzamento |
| `src/pdfbook/**` | codice di produzione, organizzato per layer (`domain/`, `extraction/`, `layout/`, `fonts/`, `translation/`, `rendering/`, `qa/`, `gui/`, `config/`) |
| `tools/**` | script di sviluppo e verifica (solo stdlib o dipendenze dev) |
| `tests/**` | test, speculari a `src/pdfbook/**` |
| `docs/**` | documentazione modulare (vedi R8) |
| `data/**` | dati non proprietari e non segreti (glossari d'esempio, fixture) |
| `legacy/**` | codice storico congelato (R12) |

Nuovi script esplorativi: **mai** in radice. Se servono una volta sola, si eseguono e si eliminano.

## R3 — Niente dati nel codice

Traduzioni, glossari, elenchi di libri, mappe di provider, soglie condivise → file in `data/` o `config/`, caricati da un modulo dedicato.
Il codice legacy viola questa regola in modo massiccio (dizionari di traduzione inline in `build_and_apply.py`, `translate_batch.py`, `translations_data.py`, `final_translate.py`). **Non replicare quel pattern**, in nessuna forma.

## R4 — Split-before-modify

Se il file da modificare supera i budget di R1: **prima** lo si splitta con un commit a comportamento invariato (estrazione pura, nessuna modifica logica), **poi** si applica la modifica richiesta. Mai "aggiungo 40 righe a un file da 700" — anche se la modifica è urgente.

## R5 — Confini di import (architettura imposta)

| Layer | Può importare |
|---|---|
| `domain` | solo stdlib |
| `config`, `qa` | `domain` |
| `extraction`, `fonts`, `layout`, `translation` | `domain` |
| `rendering` | `domain`, `fonts`, `layout` |
| `app` | `domain`, `config`, `qa`, `extraction`, `fonts`, `layout`, `translation`, `rendering` |
| `gui`, `cli` | tutto `src/pdfbook` |
| `tools`, `tests` | solo stdlib e `src/pdfbook` |
| chiunque | ❌ `legacy/**` |

Vietati: import circolari, `import *`, import con effetti collaterali, e qualunque dipendenza del layer basso da quello alto.

## R6 — Interfacce esplicite, zero magia

- Contratti in `src/pdfbook/domain/ports.py` (Protocol), strutture dati in `src/pdfbook/domain/models.py` (dataclass).
- Vietato il **monkeypatch** per iniettare dipendenze: si passa l'oggetto che implementa il Protocol.
- Vietato `from modulo import funzione` per aggirare un layer: se serve, il contratto è nel posto sbagliato.

## R7 — I test sono il contratto

- Ogni modulo pubblico ha `tests/unit/test_<modulo>.py`.
- I test non toccano rete, GPU, filesystem utente: si usa un doppio del Protocol.
- Un bug corretto senza test di regressione non è corretto: è rimandato.

## R8 — Documentazione modulare

- Indice unico: `docs/architecture/README.md`. Un file per concern, non un documento-mammut.
- Per ogni modulo: `docs/modules/<modulo>.md` (responsabilità, interfaccia, invarianti, esempio d'uso, cosa NON fa).
- Ogni nuova guida va **indicizzata** in `docs/MODULE_MAP.md` nello stesso commit.
- Livello di dettaglio: l'overview rimanda, il documento di modulo spiega. Mai duplicare lo stesso contenuto in due file.

## R9 — Aggiungere un modulo (procedura, 5 passi)

1. Crea il file nel layer corretto, entro i budget di R1, con un solo scopo.
2. Aggiungi la riga nel **registro moduli** di `docs/MODULE_MAP.md` (path, responsabilità, budget LOC, "quando aprirlo").
3. Aggiungi `docs/modules/<modulo>.md`.
4. Aggiungi `tests/unit/test_<modulo>.py`.
5. `py tools/modularity_check.py` verde.

## R10 — La mappa è la fonte di verità

Ogni modifica che cambia percorsi, responsabilità o flusso dati aggiorna `docs/MODULE_MAP.md` **nello stesso commit**. Il check automatico fallisce se esiste un modulo non mappato: la mappa non può "restare indietro".

## R11 — Segreti e contenuti proprietari

- ❌ Chiavi API nel repository, in `config.json`, nei log, in URL con `?key=`.
- ✅ Solo variabili d'ambiente / keyring; `.env.example` documenta i nomi, mai i valori.
- ❌ Testi dei libri, traduzioni complete, PDF: sono opere protette. Restano **fuori** dal repo (`.gitignore`).
- Il check fallisce su pattern di chiave, percorsi assoluti utente e file vietati tracciati.

## R12 — Zona legacy (congelata)

`legacy/**` (e i file Gen 1 oggi in radice, fino al loro spostamento) è **read-only**:

- ammessi solo bugfix critici, nessuna nuova funzionalità;
- nessun nuovo import da `src/` verso `legacy/`;
- ogni migrazione **rimuove** il file legacy corrispondente: la zona può solo restringersi.

## R13 — Niente output improvvisato

Vietati `print(...)` nel codice di produzione, `sys.stdout = io.TextIOWrapper(...)`, `except: pass`.
Logging strutturato con livelli; errori con contesto (pagina, blocco, provider).

## R14 — Dipendenze

Dichiarate solo in `pyproject.toml`, con vincoli di versione. Nessuna dipendenza opzionale silenziosa: se `pyphen` manca, il sistema lo dichiara (capacità degradata visibile), non lo nasconde.

## R15 — Commit e PR

- Conventional commits, **un commit = un modulo** (o uno split, o un test).
- La PR compila il template: *quali file ho aperto* (prova di R0), *check eseguiti*, *mappa aggiornata sì/no*.

---

## Definition of Done

- [ ] R0 rispettato: ≤2 file letti + test
- [ ] `py tools/modularity_check.py` verde
- [ ] test del modulo verdi
- [ ] `docs/MODULE_MAP.md` aggiornata
- [ ] `docs/modules/<modulo>.md` aggiornato
- [ ] nessun segreto, nessun artefatto proprietario nel diff
- [ ] nessun nuovo file alla radice, nessuna nuova funzione > 50 righe

## Se una regola non è rispettabile

Stop. Scrivi nel commit/PR **quale** regola, **perché**, e **quando** verrà rimossa l'eccezione.
Le eccezioni dichiarate sono ammesse; quelle silenziose no. Il check automatico è la rete di sicurezza, non un sostituto del giudizio.

---

## Eccezioni dichiarate attive

Regola R9 del protocollo: un'eccezione è ammessa se è **scritta, motivata e datata**. Questa tabella è l'unico posto in cui le violazioni sono tollerate.

| Zona | Regole violate | Motivo | Scadenza |
|---|---|---|---|
| `conversione gemini/` (app Gen 2 in uso) | R1 (file fino a 728 righe), R2, R3 (nessuna), R13 (`print`) | è l'applicazione funzionante; viene smontata modulo per modulo da M1 a M11 | alla chiusura di **M11** |
| `legacy/**` (53 file Gen 1) | R1, R2, R3, R13, percorsi assoluti | codice storico congelato, consultabile ma non più evoluto | rimozione a ogni migrazione (M1–M10) |
| `translations.json`, `translations_cache.json`, `extracted_text.json` | R3 (dati fuori dal codice: ✅ già così) | contengono testo di opere protette: esclusi da git | permanente (`.gitignore`) |

Il gate `--audit-all` misura queste zone ma **non** fa fallire la CI: servono a mostrare che il debito diminuisce a ogni PR di migrazione.

---

## Enforcement (chi verifica cosa)

| Regola | Verificata da |
|---|---|
| R0, R15 | template PR + revisione umana |
| R1 | `tools/modularity_check.py` (righe file, righe funzione, def top-level) |
| R2 | `modularity_check` (file `.py` in radice) |
| R3 | `modularity_check` (euristica dati inline) |
| R5 | `modularity_check` (matrice dei layer) |
| R7 | CI: `python -m unittest discover -s tests` |
| R8, R10 | `modularity_check` (moduli non mappati) + revisione |
| R11 | `modularity_check` (pattern segreti, path assoluti) + `.gitignore` |
| R12 | `modularity_check` (import da `legacy/`) |
| R13 | `modularity_check` (`print`, hack stdout, `except: pass`) |

Comandi:

```
py tools/modularity_check.py            # report sui layer di produzione
py tools/modularity_check.py --strict   # anche i debiti legacy diventano errori (CI notturna)
py tools/modularity_check.py --audit-all  # include legacy/ e i file di configurazione (audit segreti)
py -m unittest discover -s tests -v
```

Stato di partenza registrato (dopo il primo riordino): 0 errori, 53 warning R2 azzerati spostando i 53 script Gen 1 in `legacy/`.
L'audit `--audit-all` segnala le chiavi reali ancora presenti in `conversione gemini/config.json`: vanno ruotate e il file eliminato prima di qualsiasi push (vedi [`SECURITY.md`](SECURITY.md)).
