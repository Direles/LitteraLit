# Packaging (Fase 6.3)

Due modi per distribuire LitteraLit, entrambi senza installare Python sulla macchina di
destinazione:

| Cosa | Comando | Risultato |
|---|---|---|
| pacchetto Python | `python -m build` | `dist/*.whl` + `sdist` (verificati in CI dal job `package`) |
| binari desktop | `python -m PyInstaller ...` | cartella `dist/pdfbook/` (CLI) e `dist/pdfbook-gui/` (GUI) |

I binari si costruiscono **automaticamente** con la GitHub Action `.github/workflows/release.yml`
su Windows, macOS e Linux, sia a mano (`workflow_dispatch`) sia pubblicando un tag `v*`.

## Build locale

```bash
pip install -e ".[gui]" pyinstaller

python -m PyInstaller --noconfirm --clean --name pdfbook --onedir \
  --collect-all pymupdf --paths src src/pdfbook/cli.py

python -m PyInstaller --noconfirm --clean --windowed --name pdfbook-gui --onedir \
  --collect-all customtkinter --collect-all pymupdf --paths src src/pdfbook/gui/app.py
```

`--onedir` e non `--onefile`: l'avvio è immediato, l'antivirus non deve rieseguire
l'estrazione a ogni lancio e l'aggiornamento è una cartella da sostituire. La dimensione
tipica è ~90 MB per la GUI (PyMuPDF e Tk inclusi).

Verificato su Windows: `dist/pdfbook-gui/pdfbook-gui.exe` parte, `dist/pdfbook/pdfbook.exe --version`
risponde.

## Firme e avvisi

I binari **non sono firmati** (nessun certificato nel repository):

- **Windows**: SmartScreen mostra "Autore sconosciuto" → *Ulteriori informazioni* → *Esegui
  comunque*. Una release firmata richiede un certificato EV e un passo `signtool` con i
  segreti in CI.
- **macOS**: Gatekeeper blocca l'app scaricata → tasto destro → *Apri*, oppure
  `xattr -dr com.apple.quarantine /Applications/LitteraLit.app`. La notarizzazione richiede
  un account Apple Developer.
- **Linux**: nessun avviso; l'AppImage (non ancora prodotta) eviterebbe anche il `tar.gz`.

## Licenza dei binari

Il programma incorpora **PyMuPDF**, distribuito con licenza **AGPL-3.0**. Ogni binario
pubblicato è quindi un'opera combinata AGPL-3.0: la release deve offrire il sorgente
corrispondente (questo repository, allo stesso tag) e la licenza. Vedi
[`THIRD_PARTY.md`](../THIRD_PARTY.md) e [`docs/architecture/13-licenza.md`](../docs/architecture/13-licenza.md).
