# 13 — Licenza e dipendenze: la decisione aperta (Fase 6.5)

> Sezione di decisione, non di implementazione. Il codice oggi funziona; questo documento
> serve a scegliere **con quali vincoli** può essere distribuito.

## Il problema in una riga

Il progetto è MIT, ma la dipendenza centrale — **PyMuPDF** (import `pymupdf`/`fitz`) — è
distribuita con **AGPL-3.0** oppure con licenza commerciale Artifex. Un'applicazione che la
usa e viene distribuita deve rispettare l'AGPL (codice sorgente disponibile anche a chi usa il
programma via rete) oppure acquistare la licenza commerciale.

Il repository pubblico su GitHub è **conforme** all'AGPL (sorgente disponibile). Il problema
nasce con:

- una **release binaria** (PyInstaller, AppImage) senza offerta di sorgente;
- un **servizio hosted** (SaaS) che traduce libri per terzi;
- una **distribuzione commerciale** desktop.

## Le tre opzioni

### A. Restare su PyMuPDF, accettare AGPL

| Aspetto | Valutazione |
|---|---|
| Costo | 0 € |
| Tempo | 0 giorni |
| Qualità | massima: redazione, `TextWriter`, estrazione con coordinate, subsetting |
| Vincolo | tutto il prodotto (non solo il layer PDF) diventa AGPL se distribuito |
| Rischio | un cliente aziendale che non accetta AGPL non può usarlo |

È la scelta giusta se il progetto resta **open source** e non c'è pressione commerciale.

### B. Sostituire lo stack PDF (piano B già previsto in §2 dell'architettura)

| Funzione oggi | Sostituto | Note |
|---|---|---|
| estrazione testo + coordinate | `pypdfium2` + `pdfminer.six` (o `pdfplumber`) | layout e font meno ricchi: serve lavoro su `pdf_extractor` |
| redazione (rimozione testo) | `pikepdf` (qpdf) + overlay | non c'è `add_redact_annot`: si ridisegna un rettangolo bianco e si sovrappone il testo |
| disegno del testo | `ReportLab` o `borb` | shaping limitato; per RTL/CJK serve HarfBuzz (`uharfbuzz`) |
| salvataggio/subreference | `pikepdf` | solido, maturo |

| Aspetto | Valutazione |
|---|---|
| Costo | 0 € di licenza |
| Tempo | **10–15 giorni** di lavoro + regressioni sui golden |
| Qualità | inferiore su font embedded e redazione; accettabile su libri "normali" |
| Vincolo | licenze permissive (BSD/Apache/MIT) su tutto lo stack |

Va fatto **prima** di una release commerciale, non dopo: cambiare il motore di rendering a
libro già venduto significa rifare le misure di qualità.

### C. Licenza commerciale Artifex per PyMuPDF

| Aspetto | Valutazione |
|---|---|
| Costo | da chiedere ad Artifex (per prodotto/anno) |
| Tempo | 0 giorni di codice |
| Qualità | identica a oggi |
| Vincolo | canone ricorrente |

Ha senso solo se il volume commerciale giustifica il canone e il tempo di ingegneria di B vale
più del canone stesso.

## Cosa è già pronto per la sostituzione

L'architettura è stata costruita per rendere B il meno doloroso possibile:

| Punto unico | File | Superficie da riscrivere |
|---|---|---|
| apertura e estrazione | `extraction/fitz_source.py` | ~60 righe |
| font embedded | `fonts/fitz_adapter.py` | ~60 righe |
| redazione + disegno | `rendering/fitz_canvas.py` | ~120 righe |
| salvataggio + subset | `app/runtime.py` (`save`) | ~15 righe |

Tutto il resto (layout, traduzione, QA, CLI, GUI) **non importa fitz**: la sostituzione tocca
quattro file e un `Runtime`.

## Raccomandazione

1. **Ora**: restare su PyMuPDF (opzione A) — il progetto è pubblico e la CI non distribuisce binari.
2. **Prima di una release binaria o di un servizio**: decidere fra B e C. Se il prodotto è
   ancora sperimentale, B; se il tempo di ingegneria vale più del canone, C.
3. **In ogni caso**: mantenere la regola già in vigore — `fitz` solo nei quattro file sopra.
   È ciò che rende la decisione reversibile.

## Decisione presa (2026-10-25)

- [x] **A — resto su PyMuPDF e accetto l'AGPL-3.0** per le distribuzioni del prodotto
- [ ] B — sostituzione dello stack PDF (rinviata, resta l'alternativa documentata)
- [ ] C — licenza commerciale Artifex (rinviata)

Conseguenze operative, già applicate:

1. Il **codice del repository resta MIT** (`LICENSE`): chi lo riusa come libreria non eredita
   l'AGPL finché non collega PyMuPDF.
2. **Ogni distribuzione** del programma (binari, AppImage, immagine Docker, servizio hosted)
   è un'opera combinata con PyMuPDF: va distribuita con **AGPL-3.0** e con l'offerta del
   sorgente corrispondente. È scritto in [`THIRD_PARTY.md`](../../THIRD_PARTY.md) e nel README.
3. Il repository pubblico **soddisfa già** l'obbligo di sorgente: nessun passaggio extra per
   l'uso open source.
4. La regola «`fitz` solo in quattro file» resta in vigore: è ciò che rende la scelta
   reversibile se in futuro servirà una licenza permissiva (opzione B).
5. Chi vuole usare LitteraLit **come libreria** in un prodotto chiuso deve sostituire i
   quattro adapter (opzione B) oppure acquistare la licenza Artifex (opzione C).

La roadmap 6.5 è quindi **chiusa come decisione**; l'implementazione dell'opzione B, se mai
servirà, è descritta sopra e non richiede un nuovo documento.
