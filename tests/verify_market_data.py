"""
tests/verify_market_data.py
Verification script for py_market_data module.
"""
import sys
import os
import shutil
import time
from datetime import datetime, timedelta
from typing import List

# Ensure we can import from root
sys.path.append(os.getcwd())

from py_tradeobject.interface import IMarketDataProvider, BarData
from py_market_data import ChartManager

# --- Mock Provider ---
class MockProvider(IMarketDataProvider):
    def __init__(self):
        self.calls = []

    def get_historical_data(self, symbol: str, timeframe: str, lookback: str) -> List[BarData]:
        self.calls.append(f"get_history({symbol}, {timeframe}, {lookback})")
        
        # Generate some dummy data including TODAY to test "fresh" state
        now = datetime.now()
        data = []
        for i in range(5):
            # i=0: T-4, i=4: T-0 (Today)
            dt = now - timedelta(days=4-i)
            # Round to midnight for daily
            dt = datetime(dt.year, dt.month, dt.day)
            
            data.append(BarData(
                timestamp=dt,
                open=100 + i,
                high=105 + i,
                low=95 + i,
                close=102 + i,
                volume=1000 * i
            ))
        return data

    def get_current_price(self, symbol: str) -> float:
        return 150.0

# --- Test ---
def run_test():
    TEST_DIR = "./data/test_market_cache"
    
    # Clean start
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
        
    print(f"--- Initialize ChartManager (Storage: {TEST_DIR}) ---")
    provider = MockProvider()
    manager = ChartManager(storage_root=TEST_DIR, provider=provider)
    
    TICKER = "TEST_AAPL"
    
    # 1. First Call (Should Fetch)
    print("\n1. Requesting Data (First Time)...")
    bars = manager.ensure_data(TICKER, "1D")
    print(f"   Received {len(bars)} bars.")
    print(f"   Provider Calls: {provider.calls}")
    
    assert len(bars) == 5
    assert len(provider.calls) == 1
    assert os.path.exists(os.path.join(TEST_DIR, TICKER, "charts", "1D.json"))
    
    # 2. Second Call (Should Cache Hit)
    print("\n2. Requesting Data (Second Time)...")
    provider.calls = [] # Reset tracking
    bars2 = manager.ensure_data(TICKER, "1D")
    print(f"   Received {len(bars2)} bars.")
    print(f"   Provider Calls: {provider.calls}")
    
    assert len(bars2) == 5
    assert len(provider.calls) == 0 # Should be 0!
    
    # 3. Simulate Staleness
    # We manually modify the JSON file to have an old date
    print("\n3. Simulating Stale Cache...")
    json_path = os.path.join(TEST_DIR, TICKER, "charts", "1D.json")
    
    from py_market_data.storage import load_bars, save_bars
    loaded = load_bars(json_path)
    # Make them old (last year)
    for b in loaded:
        b.timestamp = b.timestamp - timedelta(days=365)
    save_bars(json_path, loaded)
    
    # 4. Request again (Should Fetch & Merge)
    print("   Requesting Data (Stale)...")
    provider.calls = []
    bars3 = manager.ensure_data(TICKER, "1D", lookback="1Y")
    print(f"   Received {len(bars3)} bars.")
    print(f"   Provider Calls: {provider.calls}")
    
    assert len(provider.calls) == 1
    # Check if Smart Duration worked: Should be something like "366 D" or "367 D"
    # because we shifted the bars back 365 days.
    assert "D" in provider.calls[0]
    assert "1Y" not in provider.calls[0] # Should NOT request a full year
    
    print(f"   Total Bars: {len(bars3)}")
    assert len(bars3) == 10
    
    print("\n--- TEST PASSED ---")

if __name__ == "__main__":
    run_test()
