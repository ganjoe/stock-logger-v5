import sys
import os
import shutil
import json
from datetime import datetime, timedelta
from typing import List, Any, Dict
from unittest.mock import MagicMock

# Adjust path to find modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from py_tradeobject.interface import IBrokerAdapter
from py_portfolio_state.live import LivePortfolioManager
from py_portfolio_state.history import HistoryFactory
from py_portfolio_state.objects import PortfolioSnapshot, PortfolioPosition
from py_tradeobject.models import TradeState, TradeStatus, TradeTransaction, TransactionType

# --- Mocks ---

class MockBroker(IBrokerAdapter):
    def get_account_summary(self) -> Dict[str, float]:
        return {
            'TotalCashValue': 50000.0,
            'NetLiquidation': 75000.0,
            'GrossPositionValue': 25000.0
        }

    def get_positions(self) -> List[Any]:
        # Mimic IBKR Position tuple behavior with a simple class or namedtuple
        class MockPos:
            def __init__(self, symbol, pos, avgCost):
                self.contract = MagicMock()
                self.contract.symbol = symbol
                self.position = pos
                self.avgCost = avgCost
        
        return [
            MockPos("AAPL", 100, 150.0), # Value: 100 * CurrentPrice
            MockPos("MSFT", -50, 300.0)  # Short
        ]

    def get_current_price(self, symbol: str) -> float:
        if symbol == "AAPL": return 160.0  # +$1000 PnL
        if symbol == "MSFT": return 290.0  # +$500 PnL (Short from 300 to 290)
        return 100.0

    # Dummies
    def place_order(self, *args, **kwargs): pass
    def get_updates(self, *args): pass
    def cancel_order(self, *args): pass
    def get_historical_data(self, *args): return []

def test_live_manager():
    print("\n--- Testing LivePortfolioManager ---")
    broker = MockBroker()
    manager = LivePortfolioManager(broker)
    
    snapshot = manager.snapshot()
    
    print(f"Snapshot Timestamp: {snapshot.timestamp}")
    print(f"Equity: {snapshot.equity} (Expected 75000.0)")
    assert snapshot.equity == 75000.0
    
    assert len(snapshot.positions) == 2
    
    aapl = next(p for p in snapshot.positions if p.ticker == "AAPL")
    assert aapl.quantity == 100
    assert aapl.market_value == 16000.0
    assert aapl.unrealized_pnl == 1000.0 # (160 - 150) * 100
    
    msft = next(p for p in snapshot.positions if p.ticker == "MSFT")
    assert msft.quantity == -50
    # Short Value is usually negative in some systems or absolute? 
    # Current implementation: market_value = qty * current_price = -50 * 290 = -14500
    assert msft.market_value == -14500.0
    # PnL = (Current - Avg) * Qty = (290 - 300) * -50 = -10 * -50 = +500
    assert msft.unrealized_pnl == 500.0
    
    print("Live Snapshot Verification PASSED")

def test_history_factory():
    print("\n--- Testing HistoryFactory ---")
    test_dir = "./data/test_history_portfolio"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # Create Dummy TradeState JSON
    ts = TradeState(id="TRD-001", ticker="GOOGL", status=TradeStatus.OPEN)
    ts.status = TradeStatus.OPEN
    # Add Transaction 1: Buy 10 @ 100 on Jan 1
    ts.transactions.append(TradeTransaction(
        id="T1", timestamp=datetime(2025, 1, 1), type=TransactionType.ENTRY,
        quantity=10, price=100.0, commission=1.0, slippage=0.0
    ))
    # Add Transaction 2: Buy 10 @ 110 on Jan 2
    ts.transactions.append(TradeTransaction(
        id="T2", timestamp=datetime(2025, 1, 2), type=TransactionType.ADJUSTMENT, # Scale In
        quantity=10, price=110.0, commission=1.0, slippage=0.0
    ))
    
    with open(os.path.join(test_dir, "GOOGL_trade.json"), 'w') as f:
        json.dump(ts.to_dict(), f)
    
    factory = HistoryFactory(trades_dir=test_dir)
    factory.load_all_trades()
    
    print(f"Loaded {len(factory._cache)} trades.")
    if factory._cache:
        t = factory._cache[0]
        print(f"Trade 0: {t.ticker}, Tx Count: {len(t.transactions)}")
        for tx in t.transactions:
            print(f"  Tx: {tx.id} @ {tx.timestamp} Qty={tx.quantity}")

    # Test Snapshot at Jan 1 (After T1, Before T2)
    snap1 = factory.get_snapshot_at(datetime(2025, 1, 1, 12, 0, 0))
    # Should have 10 qty
    print(f"Snapshot 1 (Jan 1): {len(snap1.positions)} positions")
    if snap1.positions:
        p = snap1.positions[0]
        print(f"  Ticker: {p.ticker}, Qty: {p.quantity}, AvgPrice: {p.avg_price}")
        assert p.quantity == 10
        assert p.avg_price == 100.0
    else:
        assert False, "Missing position in Snapshot 1"
        
    # Test Snapshot at Jan 3 (After T2)
    snap2 = factory.get_snapshot_at(datetime(2025, 1, 3))
    # Should have 20 qty, Avg Price (10*100 + 10*110)/20 = 105
    print(f"Snapshot 2 (Jan 3): {len(snap2.positions)} positions")
    if snap2.positions:
        p = snap2.positions[0]
        print(f"  Ticker: {p.ticker}, Qty: {p.quantity}, AvgPrice: {p.avg_price}")
        assert p.quantity == 20
        assert p.avg_price == 105.0
    else:
        assert False, "Missing position in Snapshot 2"

    print("History Factory Verification PASSED")
    
    # Cleanup
    shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_live_manager()
    test_history_factory()
