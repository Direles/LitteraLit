# Qualita misurata

> Parte dell'architettura: indice in [`README.md`](README.md). Sezioni 10.
> Regole vincolanti: [`AGENTS.md`](../../AGENTS.md).

---

## 10. Qualità misurata (dati reali dai QA report)

### 10.1 "Agile Estimating and Planning" — M. Cohn (365 pagine, run completa Gen 2)

| Metrica | Valore | Interpretazione |
|---|---|---|
| Blocchi di testo elaborati | **4.207** | |
| `perfect` (entra nelle righe originali, no overlap immagini) | **4.109 (97,7%)** | impaginazione rispettata |
| `font_reduced` | **2.043 (48,6%)** | metà dei blocchi ha richiesto riduzione corpo |
| `retranslated` (accorciata via LLM) | **3** | la riduzione del font ha quasi sempre evitato la chiamata extra |
| `overflow_shifted` | **1.094 (26,0%)** | un blocco su quattro ha spinto in basso i successivi |
| Font embedded riusati / fallback di sistema | **0 / 30** | il PDF sorgente (Acrobat Distiller, Type1) non consente riuso |
| Dimensione output | **2,8 MB** (input 2,1 MB) | `subset_fonts` + `deflate` molto efficaci |
| Pagine con almeno un'issue | **362 / 365 (99,2%)** | quasi tutte per `font_reduced` |

### 10.2 "User Story Mapping" — J. Patton (test 10 pagine, 1–3 e 10)

| Metrica | Valore | Interpretazione |
|---|---|---|
| Blocchi | 70 | |
| `perfect` | 38 (54,3%) | pagine di frontespizio/indice molto dense |
| `font_reduced` | 25 (35,7%) | titoli giganteschi (79 pt → 47,4 pt) |
| `overflow_shifted` | 13 (18,6%) | |
| Font embedded riusati / sistema | **13 / 2** | il PDF Antenna House permette il riuso |
| `untranslated_unresolved` | **177** ⚠ | valore **non attendibile**: il test offline mocka il traduttore e restituisce l'originale; inoltre è affetto dal bug di §11.2 |

### 10.3 Output storici Gen 1 (per confronto)

| File | Dim. | Pagine | Natura |
|---|---|---|---|
| `User-Story-Mapping-ITALIANO.pdf` | **176,4 MB** | 324 | raster 300 DPI: ogni pagina è un'immagine (testo non selezionabile, file ~1,6× l'originale) |
| `…-ITALIANO4.pdf` | **111,1 MB** | 324 | patch vettoriale in-place (producer originale preservato), font misti Helvetica/originali |
| `…-ITALIANO.pdf` (Cohn, prima run) | 7,0 MB | 365 | vettoriale senza `subset_fonts` |
| `…-ITALIANO2.pdf` (Cohn, run corrente) | **2,8 MB** | 365 | vettoriale con subsetting, font Arial subsettati (`PFLAVE+Arial Regular`) |

Il confronto raster vs vettoriale è la prova quantitativa del salto di qualità della Gen 2: **−63% di dimensione** e testo ricercabile.

### 10.4 Misure indipendenti sui file prodotti

I contatori interni non coprono ciò che accade *visivamente*. Due misure indipendenti, eseguite con PyMuPDF sugli output già presenti, mostrano difetti che il QA report non registra:

- **102 coppie di blocchi con sovrapposizione critica** in `Cohn-ITALIANO2.pdf` (su 6.551 blocchi) e **69** in `Patton-ITALIANO4.pdf` (su 2.986 blocchi);
- **sostituzione silenziosa di caratteri tipografici** nel percorso base-14 della Gen 1: in `Patton-ITALIANO4.pdf` le 301 em-dash presenti nei dati tradotti diventano 112 `·` e **zero** em-dash; assente in `Cohn-ITALIANO2.pdf` (175 em-dash conservate via `TextWriter`).

Dettaglio, metodologia e implicazioni per il QA: **§14.3**.

---
