# Nota tecnica — `insert_htmlbox` contro il renderer attuale (Fase 1.6)

> Esperimento riproducibile: `py tools/experiment_htmlbox.py`. Pagina sintetica 612×792,
> paragrafo di prova, area 492×240 pt, nessun dato editoriale.

## Misure

| Strategia | Corpo | Righe | Giustificato | Sillabazione | Caratteri estratti | Disegno (ms) | Fit (ms) |
|---|---|---|---|---|---|---|---|
| `TextWriter` (attuale) | 10,0 | 12 | no | sì (`pyphen`) | 100% | **1,63** | 93,98 |
| `insert_htmlbox` (candidata) | 10,0 | 12 | sì (CSS) | sì (CSS, se il font lo consente) | 100% | 5,34 | 0 |

Il tempo di *fit* della strategia attuale è alto perché l'esperimento cerca il corpo con
passi di 0,25 pt ricalcolando l'a capo a ogni tentativo (20 iterazioni): nel codice reale
`layout/fitter.py` fa lo stesso lavoro una volta per blocco, e il costo è già misurato nei
test di carico (500 pagine in pochi secondi con provider finto).

## Verdetto: **NO-GO come sostituto**, tenuto come opzione

1. **Estrazione**: pari (100% dei caratteri in entrambi i casi). Non è un motivo per cambiare.
2. **Velocità**: `TextWriter` disegna in 1,63 ms, `insert_htmlbox` in 5,34 ms (≈3×). Su 4.000
   blocchi sono secondi, ma non c'è un guadagno che li giustifichi.
3. **Qualità**: l'unico vantaggio reale è la **giustificazione** e la sillabazione gestite dal
   motore CSS. Il progetto ha già sillabazione (`pyphen`) e un fit che sceglie il corpo: la
   giustificazione, se servirà, si può ottenere anche distribuendo gli spazi fra le parole
   nel `TextWriter` (intervento locale, senza cambiare motore).
4. **Rischio**: `insert_htmlbox` impone di ripensare multi-run, colori per span, apici e
   tabelle — tutte cose che oggi funzionano e che il CSS non esprime con la stessa precisione.

**Quando rivalutarlo**: se su libri reali la giustificazione diventa un requisito di prodotto,
si implementa dietro un flag `PDFBOOK_FLOW=html` limitato ai blocchi di prosa senza stili
inline, e si confronta con i golden + SSIM prima di adottarlo.

## Come rifare l'esperimento

```bash
python tools/experiment_htmlbox.py
```

Lo script stampa la tabella e il verdetto; non tocca il repository e non richiede chiavi.
