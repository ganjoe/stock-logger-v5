# tests/test_history_reconstruction.py
import sys
import os
import shutil
from datetime import datetime, timedelta

# Path Setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from py_portfolio_state.history import HistoryFactory
from py_tradeobject.core import TradeObject
from py_market_data.manager import ChartManager

TEST_DATA_DIR = "./data/test_history_recon"

def setup_data():
    if os.path.exists(TEST_DATA_DIR):
        try: shutil.rmtree(TEST_DATA_DIR)
        except: pass
    os.makedirs(TEST_DATA_DIR, exist_ok=True)
    
    ticker = "TEST_HIST"
    t_dir = os.path.join(TEST_DATA_DIR, ticker)
    os.makedirs(t_dir, exist_ok=True)
    
    # Mock Broker
    class MockBroker:
        def place_order(self, **kwargs): return "MOCK_OID"
        def get_historical_data(self, *args): return [] # Return empty for now
        def get_updates(self, *args): return None # Not needed for enter

    trade = TradeObject(ticker=ticker, storage_dir=TEST_DATA_DIR)
    trade.set_broker(MockBroker())
    
    # Manually simulate a fill (since MockBroker logic is complex to wire up)
    from py_tradeobject.models import TradeTransaction, TransactionType, TradeStatus
    
    tx = TradeTransaction(
        id="FILL_1",
        timestamp=datetime.now() - timedelta(days=5),
        type=TransactionType.ENTRY,
        quantity=10,
        price=100.0,
        commission=1.0
    )
    trade._state.transactions.append(tx)
    trade._state.status = TradeStatus.OPEN
    trade.save()
    return TEST_DATA_DIR

def test_load_objects(data_dir):
    # Mock Provider
    class MockProvider:
        def place_order(self, **kwargs): return "MOCK_OID"
        def get_historical_data(self, *args): return [] # Return empty for now
        def get_updates(self, *args): return None 
        # get_current_price not strictly needed for this test unless HistoryFactory calls it?
        # HistoryFactory calls _get_price_at which calls trade.get_chart().
        # trade.get_chart calls ensure_data.
        
    provider = MockProvider()
    
    # Pass Provider instead of ChartManager
    factory = HistoryFactory(data_dir, provider=provider)
    factory.load_all_trades()
    
    print(f"Loaded {len(factory._cache)} trades.")
    if len(factory._cache) != 1:
        raise AssertionError("Expected 1 trade")
        
    obj = factory._cache[0]
    if not isinstance(obj, TradeObject):
        raise AssertionError("Expected TradeObject instance")
    
    # Verify Broker Injection
    if not obj.broker:
        raise AssertionError("Broker not injected into TradeObject")
        
    print(f"Trade Ticker: {obj.ticker}")
    if obj.ticker != "TEST_HIST":
        raise AssertionError("Wrong ticker")
    
    # Verify Snapshot Access
    snap = factory.get_snapshot_at(datetime.now())
    print(f"Snapshot Positions: {len(snap.positions)}")
    if len(snap.positions) != 1:
        raise AssertionError("Expected 1 position")
        
    print(f"Qty: {snap.positions[0].quantity}")
    if snap.positions[0].quantity != 10.0:
        raise AssertionError("Wrong quantity")

if __name__ == "__main__":
    try:
        path = setup_data()
        test_load_objects(path)
        print("✅ History Refactoring Verified!")
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(TEST_DATA_DIR):
            try: shutil.rmtree(TEST_DATA_DIR)
            except: pass
