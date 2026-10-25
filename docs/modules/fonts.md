# Modulo `fonts` — scelta del font per il PDF tradotto

**File**: `fonts/resolver.py`, `fonts/platform_fonts.py`, `fonts/fitz_adapter.py`
**Layer**: `fonts` — può importare `domain` (R5). `fitz` compare **solo** nell'adapter.
**Test**: `tests/unit/test_font_resolver.py` (8), `tests/unit/test_platform_fonts.py` (11)

## Responsabilità

| File | Responsabilità | Cosa NON fa |
|---|---|---|
| `resolver.py` | Cascata embedded → fuzzy → sistema → base-14, con verifica dei glifi della lingua | Non conosce percorsi di sistema, non apre PDF, non disegna |
| `platform_fonts.py` | Classificazione del nome font e percorsi per OS | Non decide *se* un font copre i glifi |
| `fitz_adapter.py` | `PdfFontSource` (estrazione) e `make_fitz_font` (factory) | Nessuna politica di scelta |

## La cascata (ordinate per qualità del risultato)

| # | Passo | Condizione | Contatore |
|---|---|---|---|
| 1 | Font **embedded** omonimo | il buffer copre tutti i caratteri test della lingua | `embedded_reused` |
| 2 | Font **embedded simile** | stessa famiglia normalizzata, stile compatibile (punteggio bold/italic/narrow) | `fuzzy_reused` |
| 3 | Font del **bundle** | famiglia riconosciuta e glifi coperti (vedi §Font bundle) | `bundle_used` |
| 4 | Font di **sistema** | primo file esistente per famiglia/stile | `system_fallback` |
| 5 | Base-14 (`helv`) | nessun font disponibile | `base14_fallback` ⚠ |

Il passaggio 1 è il motivo per cui il PDF tradotto può restare identico all'originale; il
passaggio 4 è ciò che lo degrada. I contatori finiscono nel QA report: **un `base14_fallback`
è un segnale di rischio** (il base-14 non copre em-dash e virgolette tipografiche — §14.3b
dell'architettura).

## Font bundle (Fase 1.4)

Un libro tradotto con font arbitrari di sistema cambia metrica da macchina a macchina: i test
golden non sono riproducibili e il PDF esce diverso per ogni utente. Il bundle è un insieme
piccolo e dichiarato di famiglie OFL:

| Famiglia | File | Ruolo |
|---|---|---|
| `source-serif` | `SourceSerif4-{Regular,Bold,It,BoldIt}.ttf` | serif da testo (Minion, Times, Georgia) |
| `inter` | `InterVariable.ttf` | sans-serif (solo regular) |
| `noto-serif` / `noto-sans` | `Noto{Serif,Sans}-Variable.ttf` | copertura ampia |
| `noto-arabic` | `NotoNaskhArabic-Variable.ttf` | arabo (RTL) |

```python
BundledFonts.discover(root=None)                  # PDFBOOK_FONT_DIR o assets/fonts
bundle.exact_path_for(family, bold, italic)       # solo lo stile esatto: mai bold→regular
bundle_family_for(pdf_font_name, bundle)          # MinionPro-Regular -> source-serif
```

Solo lo **stile esatto**: un grassetto non viene mai reso con il regular (sarebbe una perdita
di formattazione silenziosa); se lo stile manca si passa al font di sistema.

I binari **non sono nel repository** (vedi [`assets/fonts/README.md`](../../assets/fonts/README.md)):
si scaricano con `python tools/fetch_fonts.py` (Source Serif statica + Noto variabili, ~5 MB).
Senza bundle la cascata funziona come prima e `bundle_fonts_used` resta a zero.


## Interfaccia

```python
FontResolver(source, *, font_factory, target_lang="Italiano", platform=None, exists=None, bundle=None)
.resolve(pdf_font_name) -> font            # oggetto con text_length() e has_glyph()
.text_length(text, pdf_font_name, size) -> float
.covered(pdf_font_name) -> bool
.stats -> ResolverStats(embedded_reused, fuzzy_reused, bundle_used, system_fallback, base14_fallback)

classify(pdf_font_name) -> (family, bold, italic)      # family ∈ sans|sans-narrow|serif|mono
resolve_path(family, bold, italic, *, platform, exists) -> str | None
system_font_paths(platform) -> {family: (path, ...)}
PdfFontSource.open(pdf_path) / .page_fonts(i) / .extract_font(xref)
make_fitz_font(*, buffer=None, path=None, name=None)
```

## Invarianti

1. **Il nome è la chiave di cache**: lo stesso `pdf_font_name` risolve una sola volta (contatori inclusi).
2. Un font che non copre i glifi della lingua **non** viene usato, anche se è l'originale.
3. Un errore su un singolo xref o su un font rotto **non** interrompe la risoluzione: si degrada e si logga a `debug`.
4. Le metriche sono sempre quelle reali del font risolto (`text_length`), mai stime.

## Verifica su libro reale

Sul PDF Patton (Antenna House, font Guardian/Minion/Myriad), `FontResolver` riusa i font
embedded: `{'embedded_reused': 3, 'fuzzy_reused': 0, 'system_fallback': 0, 'base14_fallback': 0}`
con `coverage=True` per l'italiano (accenti, `—`, `–`, `’` inclusi).

## Cosa NON fa e dove andrà

- **Nessun disegno**: il rendering usa il font risolto tramite `rendering/` (M9).
- **Nessuna cache su disco dei font estratti**: da valutare se il prefetch diventa costoso su libri enormi (P4).
- **Nessun font bundle**: oggi si dipende dai font di sistema; un set di font liberi (es. Inter, Source Serif) renderizzerebbe il progetto indipendente dall'OS.

## Note per chi modifica

1. Cambiare `LANG_TEST_CHARS` significa cambiare **cosa** è considerato "coperto": aggiungere un test per ogni nuova lingua.
2. `platform_fonts` va esteso **per dati** (la tabella `SYSTEM_FONTS`), non con `if sys.platform` sparsi.
3. Non importare `fitz` fuori da `fitz_adapter.py`: il resto del layer deve restare testabile senza PyMuPDF.
