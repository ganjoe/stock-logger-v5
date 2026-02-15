#!/bin/bash
# Gemini PTA Quick-Talk Helper
# Usage: ./pta.sh "Deine Nachricht an Gemini"
# Beispiel: ./pta.sh "Wie ist mein Status?"

# Wir nutzen Client-ID 1, damit wir uns nicht mit dem laufenden Monitor (Client 0) beißen.
python3 run_paper.py --client-id=1 pta "$@"
