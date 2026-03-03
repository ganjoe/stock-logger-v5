#!/bin/bash
# pta_console.sh - Startet eine dedizierte Konsole fuer PTA Interaktion
# Ideal fuer SSH Sessions. Nutzt Client ID 99 um Konflikte zu vermeiden.

echo "Starte Stock-Logger Konsole (Client ID 99)..."
echo "Tippe 'chat' um mit Gemini zu sprechen."
echo "Tippe 'help' fuer eine Befehlsuebersicht."

# Wechsel in das Verzeichnis des Skripts (Projekt-Root)
cd "$(dirname "$0")"

# Automatisches Erkennen der virtuellen Umgebung
if [ -d ".venv" ]; then
    PYTHON_EXEC="./.venv/bin/python"
else
    PYTHON_EXEC="python3"
fi

# Startet die Session mit dem neuen Unified Entry Point
$PYTHON_EXEC run_logger.py --mode=human
