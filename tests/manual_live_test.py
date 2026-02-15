# tests/manual_live_test.py
import sys
import os

# Adjust path to find modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from py_captrader import session
from py_captrader.adapter import CapTraderAdapter
from py_portfolio_state.live import LivePortfolioManager

def run():
    print("--- MANUAL LIVE TEST ---")
    try:
        # 1. Get Active Session (Must be started via run_live/run_paper)
        # However, since this is a separate script, we can't share memory with the running run_live process easily unless we attach to it.
        # But the user said "ich hab über run_live.py eine verbindung hergestellt".
        # If run_live.py is running in a terminal, this script here is a SEPARATE process.
        # It cannot access the object from the other process.
        # UNLESS the user means "I want to connect to the TWS that run_live opened (or is open)".
        # Since TWS accepts multiple connections per clientID, or we use a different client ID?
        # But run_live uses client_id=0.
        # We should use a different client_id here to avoiding conflict if run_live is still running?
        # Or does the user mean they want to run a test script THAT connects?
        
        # Let's assume this script connects on its own using the standard session logic.
        # We will use client_id=999 to avoid kicking out the main app
        
        HOST = "127.0.0.1"
        PORT = 4001 # Live Port
        # PORT = 4002 # Paper Port - fallback?
        
        print(f"Connecting to {HOST}:{PORT} (ID: 999)...")
        session.connect(HOST, PORT, 999)
        
        client = session.get_active_client()
        adapter = CapTraderAdapter(client)
        manager = LivePortfolioManager(adapter)
        
        print("Fetching Snapshot...")
        snap = manager.snapshot()
        
        print("\n--- SNAPSHOT RESULT ---")
        print(f"Equity: ${snap.equity:.2f}")
        print(f"Cash:   ${snap.cash:.2f}")
        print(f"Positions: {len(snap.positions)}")
        for p in snap.positions:
            print(f" - {p.ticker}: {p.quantity} @ {p.avg_price:.2f} | PnL: {p.unrealized_pnl:.2f}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.disconnect()

if __name__ == "__main__":
    run()
