# run_paper.py - Startet die Anwendung im PAPER TRADING Modus
import sys
import argparse
from py_captrader import session, services
from py_captrader.adapter import CapTraderAdapter
from main_cli import main

def start_paper():
    parser = argparse.ArgumentParser(add_help=False) # Partial parser
    parser.add_argument("--client-id", type=int, default=0, help="Override Client ID")
    args, unknown = parser.parse_known_args()
    
    # Clean up sys.argv so main_cli doesn't complain about --client-id
    sys.argv = [sys.argv[0]] + unknown
    
    print(f"\n🟦 --- STARTING PAPER LOGIC (Localhost:4002 ClientID:{args.client_id}) ---")
    
    try:
        # 1. Verbindung herstellen (Explizit via Session)
        session.connect(host="127.0.0.1", port=4002, client_id=args.client_id)
        
        # 2. Broker Adapter erstellen & REGISTRIEREN (Services)
        client = session.get_active_client()
        adapter = CapTraderAdapter(client)
        services.register_broker(adapter)
        
        # 3. Main CLI starten
        main()
        
    except Exception as e:
        print(f"❌ CRITICAL LOAD ERROR: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    start_paper()
