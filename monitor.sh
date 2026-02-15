#!/bin/bash
# Terminal 1: Passive Monitoring
# Verbindet sich als Client 0 und hält die Verbindung offen.
# Hier erscheinen die Log-Nachrichten (Verbindungen, Order Actions, Errors).
# Du musst hier nichts tippen.

echo "🔵 Starte Passive Monitor (Client 0)... Logs will appear here."
python3 run_paper.py --client-id=0
