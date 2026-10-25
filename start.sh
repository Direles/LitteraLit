#!/bin/sh
# Avvio su Linux: crea/usa .venv e apre la GUI.
cd "$(dirname "$0")" || exit 1
exec python3 tools/launch.py "$@"
