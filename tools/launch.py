"""Avvio guidato del programma (doppio clic), su Windows, macOS e Linux.

I lanciatori di sistema (``start.cmd``, ``start.command``, ``start.sh``) chiamano questo
script, che:

1. trova un interprete Python adatto al sistema;
2. crea ``.venv`` e installa il pacchetto (solo al primo avvio);
3. avvia la GUI (o la CLI, se riceve argomenti);
4. se qualcosa manca, spiega cosa fare e aspetta un tasto prima di chiudersi.

Le funzioni pure (percorsi, comandi) sono testate in ``tests/unit/test_launch_tool.py``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT / ".venv"
PROBE = "import pdfbook, customtkinter"
INSTALL_ARGS = ("-m", "pip", "install", "--quiet", "-e", ".[gui]")

__all__ = [
    "cli_command",
    "main",
    "venv_python",
]


def venv_python(venv_dir: Path, platform: str | None = None) -> Path:
    """Percorso dell'interprete dentro un virtualenv, per piattaforma."""
    current = platform or sys.platform
    if current.startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def python_candidates(platform: str | None = None) -> list[list[str]]:
    """Comandi da provare per creare il virtualenv."""
    current = platform or sys.platform
    if current.startswith("win"):
        return [["py", "-3"], ["python"]]
    return [["python3"], ["python"]]


def cli_command(args: list[str]) -> list[str]:
    """Argomenti per ``python -m pdfbook.cli``: GUI se non ci sono argomenti."""
    return ["-m", "pdfbook.cli", *(args or ["gui"])]


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    interpreter = venv_python(VENV_DIR)
    if not interpreter.exists():
        interpreter = _create_venv() or interpreter
    if interpreter.exists() and not _probe(interpreter):
        _install(interpreter)
    if interpreter.exists() and _probe(interpreter):
        return _run([str(interpreter), *cli_command(args)])
    return _fallback(args)


def _create_venv() -> Path | None:
    print("Primo avvio: creo l'ambiente virtuale (.venv)...", flush=True)
    for launcher in python_candidates():
        try:
            result = subprocess.run([*launcher, "-m", "venv", str(VENV_DIR)], cwd=ROOT)
        except FileNotFoundError:
            continue
        interpreter = venv_python(VENV_DIR)
        if result.returncode == 0 and interpreter.exists():
            return interpreter
    print("Non riesco a creare il virtualenv. Installalo con: python -m venv .venv")
    return None


def _probe(interpreter: Path) -> bool:
    result = subprocess.run([str(interpreter), "-c", PROBE], cwd=ROOT, capture_output=True)
    return result.returncode == 0


def _install(interpreter: Path) -> None:
    print("Installo le dipendenze (una volta sola, serve internet)...", flush=True)
    subprocess.run([str(interpreter), *INSTALL_ARGS], cwd=ROOT)


def _run(command: list[str]) -> int:
    return subprocess.run(command, cwd=ROOT).returncode


def _fallback(args: list[str]) -> int:
    """Ultima possibilità: Python di sistema con il pacchetto sorgente nel path."""
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    check = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=env, capture_output=True)
    if check.returncode != 0:
        print("\nImpossibile avviare il programma: mancano le dipendenze.")
        print("Prova manualmente:")
        print(f'  cd "{ROOT}"')
        print("  python -m venv .venv")
        print("  .venv\\Scripts\\activate   (su macOS/Linux: source .venv/bin/activate)")
        print('  pip install -e ".[gui]"')
        return 1
    return _run([sys.executable, *cli_command(args)])


if __name__ == "__main__":
    code = main()
    if code and os.environ.get("PDFBOOK_LAUNCHER_PAUSE", "1") == "1" and sys.stdin.isatty():
        input("\nPremi Invio per chiudere...")
    sys.exit(code)
