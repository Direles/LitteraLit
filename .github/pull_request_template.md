## Cosa cambia

<!-- una frase: quale modulo, quale comportamento -->

## Routing (prova di R0)

| | |
|---|---|
| File aperti | <!-- elenco: max 2 + test --> |
| Modulo responsabile (da MODULE_MAP) | |
| Nuovi moduli creati | <!-- nessuno / elenco + riga nel registro --> |

## Check eseguiti

- [ ] `py tools/modularity_check.py` verde
- [ ] `py -m unittest discover -s tests -v` verde
- [ ] `docs/MODULE_MAP.md` aggiornata (registro moduli / routing)
- [ ] `docs/modules/<modulo>.md` aggiornato
- [ ] nessun segreto, nessun PDF/traduzione nel diff
- [ ] nessun file di codice nuovo alla radice
- [ ] nessuna funzione > 50 righe, nessun file > 300 righe

## Eccezioni dichiarate

<!-- regola non rispettata, perché, quando viene rimossa. Nessuna eccezione silenziosa. -->
