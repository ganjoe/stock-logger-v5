# run_live.py - Startet die Anwendung im LIVE TRADING Modus
import sys
from py_captrader import session, services
from py_captrader.adapter import CapTraderAdapter
from main_cli import main

def start_live():
    print("\n🟥 --- STARTING LIVE LOGIC (Localhost:4001) ---")
    print("⚠️ WARNING: REAL MONEY TRADING. User Confirmation Required.")
    confirm = input("Type 'LIVE' to confirm connection: ")
    if confirm != "LIVE":
        print("Safety Abort.")
        return

    try:
        # 1. Verbindung herstellen (Explizit via Session)
        session.connect(host="127.0.0.1", port=4001, client_id=0)
        
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
    start_live()
