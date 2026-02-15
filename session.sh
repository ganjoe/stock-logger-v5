#!/bin/bash
# Startet eine INTERAKTIVE Sitzung mit dem PTA (Client 1)
# Hier kannst du tippen: pta "Deine Nachricht"
# Und du bleibst im Session-Kontext.

echo "🔵 Starte Interaktive PTA-Session (Client 1)..."
echo "Tippe: pta 'Status' oder pta 'Lösche Order 101'"
echo "Beenden mit: exit"
echo ""

python3 run_paper.py --client-id=1
