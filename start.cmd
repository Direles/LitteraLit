@echo off
rem Avvio con doppio clic su Windows: crea/usa .venv e apre la GUI.
rem Accetta gli stessi argomenti della CLI (es. "start.cmd doctor").
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "tools\launch.py" %*
) else (
    python "tools\launch.py" %*
)

if errorlevel 1 pause
endlocal
