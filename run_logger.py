# run_logger.py - Unified Entry Point (Connection 3.0)
# Starts the Systems "Offline". Connection is handled by PTA.

import sys
import argparse
# from py_captrader import session # No auto-connect
from main_cli import main

def start_system():
    print(f"\n🚀 --- SYSTEM START (Offline Mode) ---")
    print(f"ℹ️  Waiting for PTA to establish connection...")
    
    try:
        # Start Main CLI (PTA / ChatOps) straight away
        # Connection will be initiated via 'connect' command inside the chat
        main()
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_system()
