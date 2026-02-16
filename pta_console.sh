#!/bin/bash
# pta_console.sh - Startet eine dedizierte Konsole fuer PTA Interaktion
# Ideal fuer SSH Sessions. Nutzt Client ID 99 um Konflikte zu vermeiden.

echo "Starte Stock-Logger Konsole (Client ID 99)..."
echo "Tippe 'chat' um mit Gemini zu sprechen."
echo "Tippe 'help' fuer eine Befehlsuebersicht."

# Wechsel in das Verzeichnis des Skripts (Projekt-Root)
cd "$(dirname "$0")"


# Startet die Session mit dem neuen Unified Entry Point (ID 0 enforced by script, but we pass args if needed)
# Actually run_logger.py enforces ID 0 internally.
python3 run_logger.py --mode=human
