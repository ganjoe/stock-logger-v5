import sys
import os
import shutil
from unittest.mock import MagicMock
from datetime import datetime

# Adjust path to find modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from py_tradeobject.core import TradeObject
from py_tradeobject.models import TradeStatus
from py_tradeobject.interface import IBrokerAdapter

# Mock Broker
class MockBroker(IBrokerAdapter):
    def __init__(self):
        self.orders = {}
        self.counter = 0
        
    def place_order(self, order_ref, symbol, quantity, limit_price=None, stop_price=None) -> str:
        self.counter += 1
        oid = f"ORD-{self.counter}"
        print(f"[Broker] Placing Order {oid}: Qty={quantity} Lmt={limit_price} Stp={stop_price}")
        return oid
        
    def cancel_order(self, order_id: str):
        print(f"[Broker] Cancelling Order {order_id}")

    # Dummy implementations for abstract methods
    def get_portfolio_updates(self, account_id: str): pass
    def get_order_updates(self, order_ref: str): pass
    def get_updates(self, *args): pass # Fix for abstract method error
    def get_historical_data(self, *args): return []
    def get_current_price(self, *args): return 100.0

def test_order_logging():
    print("--- Testing TradeObject Order Logging ---")
    
    # 1. Setup
    test_dir = "./data/test_trades_logging"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        
    from py_tradeobject.models import TradeTransaction, TransactionType

    broker = MockBroker()
    trade = TradeObject("AAPL", storage_dir=test_dir)
    # trade.metrics.net_quantity = 10 # This is ignored by dynamic calculation
    
    # Simulate a filled entry transaction
    trade._state.transactions.append(TradeTransaction(
        id="EXEC-1",
        timestamp=datetime.now(),
        type=TransactionType.ENTRY,
        quantity=10,
        price=150.0,
        commission=1.0,
        slippage=0.0
    ))
    
    # Inject Broker
    # Note: TradeObject usually requires a provider via some mechanism or we just set it manually for testing logic
    trade.broker = broker
    
    # 2. Entry
    print("\n1. Executing Enter...")
    trade.enter(quantity=10, limit_price=150.0, stop_loss=140.0)
    
    # Verify Logs
    history = trade._state.order_history
    assert len(history) == 2, f"Expected 2 logs (Entry + Stop), got {len(history)}"
    
    entry_log = history[0]
    assert entry_log.action == "BUY"
    assert entry_log.quantity == 10
    assert entry_log.limit_price == 150.0
    assert entry_log.type == "LMT"
    assert entry_log.note == "Initial Entry"
    
    stop_log = history[1]
    assert stop_log.action == "SELL" # Stop for Buy is Sell
    assert stop_log.quantity == -10
    assert stop_log.stop_price == 140.0
    assert stop_log.type == "STP"
    assert stop_log.note == "Initial Stop"
    
    print("   Entry Logs Verified.")
    
    # 3. Adjust Stop
    print("\n2. Executing Set Stop Loss (Trail)...")
    # Simulate a fill so net_quantity is valid? 
    # TradeObject check for set_stop_loss uses metrics.net_quantity.
    # In this mock, we manually set it above.
    
    trade.set_stop_loss(145.0)
    
    history = trade._state.order_history
    assert len(history) == 3, f"Expected 3 logs, got {len(history)}"
    
    adj_log = history[2]
    assert adj_log.action == "SELL"
    assert adj_log.stop_price == 145.0
    assert adj_log.note == "Stop Adjustment"
    
    print("   Adjustment Log Verified.")
    
    # 4. Persistence
    print("\n3. Testing Persistence...")
    trade.save()
    
    trade2 = TradeObject("AAPL", id=trade.id, storage_dir=test_dir)
    assert len(trade2._state.order_history) == 3
    print("   Persistence Verified.")

    print("\n--- TEST PASSED ---")

if __name__ == "__main__":
    test_order_logging()
