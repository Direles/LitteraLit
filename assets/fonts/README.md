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
| `inter` | `Inter-{Regular,Bold,Italic,BoldItalic}.ttf` | sans-serif (Helvetica, Arial, Franklin) |
| `source-serif` | `SourceSerif4-{Regular,Bold,It,BoldIt}.ttf` | serif da testo (Minion, Times, Georgia) |
| `noto-serif` | `NotoSerif-{Regular,Bold,Italic,BoldItalic}.ttf` | copertura ampia |
| `noto-sans` | `NotoSans-{Regular,Bold,Italic,BoldItalic}.ttf` | copertura ampia, sans |

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
