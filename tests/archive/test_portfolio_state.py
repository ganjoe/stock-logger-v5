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

    def get_all_open_orders(self) -> List[Any]:
        # Mimic ib_insync Trade objects
        class MockOrder:
            def __init__(self, orderId, action, orderType, totalQuantity, lmtPrice=0.0, auxPrice=0.0, orderRef=""):
                self.orderId = orderId
                self.action = action
                self.orderType = orderType
                self.totalQuantity = totalQuantity
                self.lmtPrice = lmtPrice
                self.auxPrice = auxPrice
                self.orderRef = orderRef

        class MockTrade:
            def __init__(self, symbol, orderId, action, orderType, qty, lmt=0.0, aux=0.0, ref=""):
                self.contract = MagicMock()
                self.contract.symbol = symbol
                self.order = MockOrder(orderId, action, orderType, qty, lmt, aux, ref)

        return [
            MockTrade("AAPL", 1001, "BUY", "LMT", 10, lmt=155.0, ref="TRD-AAPL-1"),
            MockTrade("TSLA", 1002, "SELL", "STP", 20, aux=200.0, ref="TRD-TSLA-1") # Stop Order
        ]

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
    
    # 1. Positions
    assert len(snapshot.positions) == 2
    
    aapl_pos = next(p for p in snapshot.positions if p.ticker == "AAPL")
    assert aapl_pos.quantity == 100
    assert aapl_pos.market_value == 16000.0
    
    # 2. Orders
    assert len(snapshot.active_orders) == 2
    
    aapl_order = next(o for o in snapshot.active_orders if o.ticker == "AAPL")
    assert aapl_order.qty == 10
    assert aapl_order.price == 155.0 # lmtPrice
    assert aapl_order.trade_id == "TRD-AAPL-1"
    
    tsla_order = next(o for o in snapshot.active_orders if o.ticker == "TSLA")
    assert tsla_order.qty == 20
    assert tsla_order.price == 200.0 # auxPrice (Stop)
    assert tsla_order.trade_id == "TRD-TSLA-1"
    
    print("Live Snapshot (Positions + Orders) Verification PASSED")

def test_history_factory():
    print("\n--- Testing HistoryFactory ---")
    test_dir = "./data/test_history_portfolio"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # Create Dummy TradeState JSON in Ticker Subdir
    ticker = "GOOGL"
    ticker_dir = os.path.join(test_dir, ticker)
    os.makedirs(ticker_dir)
    
    ts = TradeState(id="TRD-001", ticker=ticker, status=TradeStatus.OPEN)
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
    
    # Add Order Log for T2 (Stop Loss created on Jan 2)
    from py_tradeobject.models import TradeOrderLog
    ts.order_history.append(TradeOrderLog(
        timestamp=datetime(2025, 1, 2, 10, 0),
        order_id="ORD-T2",
        status="SUBMITTED",
        action="SELL",
        message="Stop Loss Placed",
        quantity=20.0,
        type="STP",
        limit_price=None,
        stop_price=95.0,
        details={}
    ))
    
    with open(os.path.join(ticker_dir, "TRD-001.json"), 'w') as f:
        json.dump(ts.to_dict(), f)
    
    factory = HistoryFactory(trades_dir=test_dir)
    factory.load_all_trades()
    
    # ... (Loaded check) ...

    # Test Snapshot at Jan 1 (After T1, Before T2)
    snap1 = factory.get_snapshot_at(datetime(2025, 1, 1, 12, 0, 0))
    # Should have 10 qty, 0 orders (T2 order not yet created)
    print(f"Snapshot 1 (Jan 1): {len(snap1.positions)} positions, {len(snap1.active_orders)} orders")
    assert len(snap1.active_orders) == 0
    if snap1.positions:
        p = snap1.positions[0]
        assert p.quantity == 10

    # Test Snapshot at Jan 3 (After T2 and Order Log)
    snap2 = factory.get_snapshot_at(datetime(2025, 1, 3))
    # Should have 20 qty, 1 active order (Stop Loss)
    print(f"Snapshot 2 (Jan 3): {len(snap2.positions)} positions, {len(snap2.active_orders)} orders")
    assert len(snap2.active_orders) == 1
    o = snap2.active_orders[0]
    assert o.order_id == "ORD-T2"
    assert o.price == 95.0
    
    # Check Jan 3 position
    if snap2.positions:
        p = snap2.positions[0]
        assert p.quantity == 20

    # Test Daily Series (F-PS-070)
    print("Testing get_daily_snapshots...")
    start = datetime(2025, 1, 1)
    end = datetime(2025, 1, 3)
    dailies = factory.get_daily_snapshots(start, end)
    
    print(f"Daily Snapshots Generated: {len(dailies)}")
    assert len(dailies) == 3 # Jan 1, Jan 2, Jan 3
    
    # Check Jan 1 (10 qty)
    assert dailies[0].timestamp.day == 1
    assert dailies[0].positions[0].quantity == 10
    
    # Check Jan 2 (After T2, 20 qty)
    assert dailies[1].timestamp.day == 2
    assert dailies[1].positions[0].quantity == 20
    
    # Check Jan 3 (Still 20 qty)
    assert dailies[2].timestamp.day == 3
    assert dailies[2].positions[0].quantity == 20

    # Check Jan 3 (Still 20 qty)
    assert dailies[2].timestamp.day == 3
    assert dailies[2].positions[0].quantity == 20

    # Test Closed Trade Aggregator (F-PS-080)
    print("Testing get_closed_trades...")
    # Add a CLOSED trade
    ts_closed = TradeState(id="TRD-CLOSED-001", ticker="MSFT", status=TradeStatus.CLOSED)
    # Buy 10 @ 200
    ts_closed.transactions.append(TradeTransaction(
        id="T3", timestamp=datetime(2025, 1, 5), type=TransactionType.ENTRY,
        quantity=10, price=200.0, commission=1.0, slippage=0.0
    ))
    # Sell 10 @ 220
    ts_closed.transactions.append(TradeTransaction(
        id="T4", timestamp=datetime(2025, 1, 10), type=TransactionType.EXIT,
        quantity=-10, price=220.0, commission=1.0, slippage=0.0
    ))
    
    # Save it
    with open(os.path.join(test_dir, "MSFT_closed.json"), 'w') as f:
        json.dump(ts_closed.to_dict(), f)
        
    # Reload factory to pick up new file
    factory.load_all_trades()
    
    # Query Window covering Jan 10
    closed_trades = factory.get_closed_trades(datetime(2025, 1, 1), datetime(2025, 1, 31))
    
    print(f"Closed Trades Found: {len(closed_trades)}")
    assert len(closed_trades) == 1
    result = closed_trades[0]
    assert result.ticker == "MSFT"
    assert result.duration_days == 5
    # PnL: (-10*200 -1) + (-(-10)*220 -1) = -2001 + 2199 = +198
    print(f"PnL: {result.pnl_absolute}")
    assert result.pnl_absolute == 198.0

    print("History Factory Verification PASSED")
    
    # Cleanup
    shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_live_manager()
    test_history_factory()
