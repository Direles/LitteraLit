# Font del bundle (OFL)

I font in questa cartella **non sono nel repository**: pesano e la licenza OFL richiede che
l'attribuzione viaggi con i binari. Si scaricano con:

```bash
python tools/fetch_fonts.py            # tutte le famiglie mancanti
python tools/fetch_fonts.py --check    # solo verifica
```

## Famiglie e ruoli

| Famiglia | File attesi | Ruolo |
|---|---|---|
| `source-serif` | `SourceSerif4-{Regular,Bold,It,BoldIt}.ttf` (statici) | serif da testo (Minion, Times, Georgia) |
| `inter` | `InterVariable.ttf` | sans-serif, solo regular |
| `noto-serif` / `noto-sans` | `Noto{Serif,Sans}-Variable.ttf` | copertura ampia (latino, greco, cirillico) |
| `noto-arabic` | `NotoNaskhArabic-Variable.ttf` | arabo (RTL) |

L'ebraico e il CJK restano fuori dal bundle: i Noto variabili espongono l'istanza *Thin* (peggio
del font di sistema) e il Serif CJK pesa ~25 MB per lingua. Per quei libri si usano i font
del sistema operativo.

## Cosa serve davvero il bundle

| Caso | Serve? |
|---|---|
| Libro latino su una macchina con font di sistema normali | **no**: la cascata usa i font embedded del PDF, poi quelli di sistema |
| Output riproducibile identico su macchine diverse (golden, confronti SSIM) | **sì**: le metriche non dipendono dall'OS |
| Libro con arabo (shaping via HTML) | **no**: il shaping risolve i nomi di famiglia tramite il sistema operativo, non legge questa cartella |
| Font del libro assente dal sistema (es. Minion) | **sì**, se vuoi una serif coerente invece di quella di ripiego |

## Come vengono usati

`fonts/bundled.py` mappa il nome font del PDF sulla famiglia del bundle
(`MinionPro-Regular` → `source-serif`, `Helvetica` → `inter`). La cascata in
`fonts/resolver.py` è:

1. font **embedded** nel PDF (identico all'originale);
2. **bundle** (metriche stabili, stesse su ogni macchina);
3. **font di sistema**;
4. base-14 (ultima spiaggia, segnalata come `base14_fallback`).

Se la cartella è vuota la cascata funziona come prima: nessun errore, i contatori
`bundle_fonts_used` restano a zero.

## Licenze

Tutte le famiglie sono SIL Open Font License 1.1. Quando distribuisci i binari, aggiungi
accanto a loro il testo `OFL.txt` della famiglia e l'attribuzione dell'autore. Il file
`OFL.txt` **può** stare nel repository; i `.ttf` no.
