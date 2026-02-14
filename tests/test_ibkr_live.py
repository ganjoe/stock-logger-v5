"""
tests/test_ibkr_live.py
Live test for py_market_data with IBKR connection.
Requires running TWS/Gateway on port 4002.
"""
import sys
import os
import time

# Ensure root is in path
sys.path.append(os.getcwd())

from py_captrader.client import IBKRClient
from py_captrader.adapter import CapTraderAdapter
from py_market_data import ChartManager

def run_live_test():
    HOST = "127.0.0.1"
    PORT = 4002
    CLIENT_ID = 99 # Test ID
    
    print(f"--- Connecting to IBKR ({HOST}:{PORT}) ---")
    try:
        client = IBKRClient(host=HOST, port=PORT, client_id=CLIENT_ID)
        client.connect()
    except Exception as e:
        print(f"ERROR: Could not connect to IBKR: {e}")
        print("Make sure TWS/Gateway is running and API is enabled on port 4002.")
        return

    adapter = CapTraderAdapter(client)
    
    # Use a temp cache dir to ensure we fetch fresh data
    CACHE_DIR = "./data/live_test_cache"
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        
    manager = ChartManager(storage_root=CACHE_DIR, provider=adapter)
    
    TICKER = "AAPL"
    TIMEFRAME = "1D"
    
    print(f"\nRequests 10 days of {TIMEFRAME} data for {TICKER}...")
    try:
        # We ask for 1M lookback just to be safe, but only show last 10
        bars = manager.ensure_data(TICKER, timeframe=TIMEFRAME, lookback="1M")
        
        print(f"Received {len(bars)} bars total.")
        print("-" * 60)
        print(f"{'Date':<12} | {'Open':<10} | {'High':<10} | {'Low':<10} | {'Close':<10} | {'Volume':<12}")
        print("-" * 60)
        
        # Show last 10
        for b in bars[-10:]:
            date_str = b.timestamp.strftime("%Y-%m-%d")
            print(f"{date_str:<12} | {b.open:<10.2f} | {b.high:<10.2f} | {b.low:<10.2f} | {b.close:<10.2f} | {b.volume:<12.0f}")
            
        print("-" * 60)
        print("Success.")
        
    except Exception as e:
        print(f"ERROR fetching data: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\nDisconnecting...")
        client.disconnect()

if __name__ == "__main__":
    run_live_test()
