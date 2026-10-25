# Dipendenze e licenze di terze parti

Il **codice** di LitteraLit è distribuito con licenza MIT (vedi [`LICENSE`](LICENSE)).
Questo file elenca le dipendenze e spiega l'unica conseguenza non ovvia: **PyMuPDF è AGPL-3.0**,
quindi ogni *distribuzione del programma* (non del solo codice) è un'opera combinata AGPL.

## Runtime

| Dipendenza | Licenza | Uso nel progetto | Conseguenza |
|---|---|---|---|
| **PyMuPDF** (`pymupdf`) | **AGPL-3.0** o commerciale Artifex | apertura PDF, estrazione, redazione, disegno, salvataggio | **la distribuzione del programma è AGPL-3.0**; obbligo di offrire il sorgente corrispondente |
| pyphen | GPL-2.0+/LGPL-2.1+/MPL-1.1 (tri-licenza) | sillabazione | compatibile con AGPL scegliendo GPL o MPL |
| requests | Apache-2.0 | HTTP verso i provider | compatibile |
| customtkinter (extra `gui`) | MIT | interfaccia desktop | compatibile |
| pillow (extra `imaging`) | HPND (permissiva) | immagini per il QA visivo | compatibile |
| Tesseract + ocrmypdf (opzionali, non Python) | Apache-2.0 / GPL-3.0 | OCR delle scansioni | eseguiti come processi esterni, non linkati |

## Font del bundle (opzionali, non nel repository)

| Famiglia | Licenza | Nota |
|---|---|---|
| Inter | SIL OFL 1.1 | scaricata con `python tools/fetch_fonts.py` |
| Source Serif 4 | SIL OFL 1.1 | idem |
| Noto Serif / Noto Sans | SIL OFL 1.1 | idem |

La OFL permette l'uso e la ridistribuzione dei binari **solo insieme** al testo della licenza:
per questo i `.ttf` non sono versionati e `assets/fonts/README.md` spiega come aggiungerli con
la loro licenza.

## Cosa significa in pratica

| Scenario | Cosa devi fare |
|---|---|
| Uso personale o interno | nulla |
| Fork e modifica del repository pubblico | mantieni il sorgente disponibile: nulla di più |
| Distribuzione di un binario (PyInstaller, AppImage, Docker) | distribuisci sotto **AGPL-3.0** e offri il sorgente corrispondente (il repository è sufficiente finché è pubblico e allineato) |
| Servizio hosted che traduce per terzi | AGPL-3.0: gli utenti del servizio devono poter ottenere il sorgente |
| Prodotto chiuso che usa LitteraLit come libreria | serve l'opzione B (sostituire PyMuPDF) o C (licenza commerciale Artifex), vedi [`docs/architecture/13-licenza.md`](docs/architecture/13-licenza.md) |

Il testo completo dell'AGPL-3.0 è disponibile su <https://www.gnu.org/licenses/agpl-3.0.html>.
PyMuPDF: <https://github.com/pymupdf/PyMuPDF> (licenza e opzioni commerciali Artifex).
