# import pytest
from datetime import datetime
from unittest.mock import MagicMock
from py_portfolio_state.live import LivePortfolioManager
from py_portfolio_state.objects import PortfolioSnapshot
from py_tradeobject.interface import IBrokerAdapter

class MockPosition:
    def __init__(self, symbol, qty, avg_cost):
        self.contract = MagicMock()
        self.contract.symbol = symbol
        self.position = qty
        self.avgCost = avg_cost

class MockOrder:
    def __init__(self, symbol, order_id, action, qty, price, ref=""):
        self.contract = MagicMock()
        self.contract.symbol = symbol
        self.order = MagicMock()
        self.order.orderId = order_id
        self.order.action = action
        self.order.orderType = "LMT"
        self.order.totalQuantity = qty
        self.order.lmtPrice = price
        self.order.auxPrice = 0.0
        self.order.orderRef = ref

def test_live_portfolio_filter():
    # 1. Setup Mock Broker
    broker = MagicMock(spec=IBrokerAdapter)
    broker.get_account_summary.return_value = {"TotalCashValue": 10000.0, "NetLiquidation": 15000.0}
    
    # 2 positions: AAPL and MSFT
    broker.get_positions.return_value = [
        MockPosition("AAPL", 10, 150.0),
        MockPosition("MSFT", 5, 300.0)
    ]
    
    # 2 orders: AAPL and MSFT
    trade_aapl = MagicMock()
    trade_aapl.contract.symbol = "AAPL"
    trade_aapl.order.orderId = 1
    trade_aapl.order.action = "BUY"
    trade_aapl.order.orderType = "LMT"
    trade_aapl.order.totalQuantity = 5
    trade_aapl.order.lmtPrice = 145.0
    trade_aapl.order.auxPrice = 0.0
    trade_aapl.order.orderRef = "TRD-1"

    trade_msft = MagicMock()
    trade_msft.contract.symbol = "MSFT"
    trade_msft.order.orderId = 2
    trade_msft.order.action = "SELL"
    trade_msft.order.orderType = "LMT"
    trade_msft.order.totalQuantity = 2
    trade_msft.order.lmtPrice = 310.0
    trade_msft.order.auxPrice = 0.0
    trade_msft.order.orderRef = "TRD-2"

    broker.get_all_open_orders.return_value = [trade_aapl, trade_msft]
    broker.get_current_price.return_value = 160.0 # Standard price for all

    manager = LivePortfolioManager(broker)
    # Mock save_snapshot to avoid file I/O
    manager.save_snapshot = MagicMock()

    # --- Test 1: No Filter ---
    snap_full = manager.snapshot()
    assert len(snap_full.positions) == 2
    assert len(snap_full.active_orders) == 2

    # --- Test 2: AAPL Filter ---
    snap_aapl = manager.snapshot(ticker="AAPL")
    assert len(snap_aapl.positions) == 1
    assert snap_aapl.positions[0].ticker == "AAPL"
    assert len(snap_aapl.active_orders) == 1
    assert snap_aapl.active_orders[0].ticker == "AAPL"

    # --- Test 3: MSFT Filter ---
    snap_msft = manager.snapshot(ticker="MSFT")
    assert len(snap_msft.positions) == 1
    assert snap_msft.positions[0].ticker == "MSFT"
    assert len(snap_msft.active_orders) == 1
    assert snap_msft.active_orders[0].ticker == "MSFT"

    # --- Test 4: Unknown Ticker ---
    snap_none = manager.snapshot(ticker="GOOGL")
    assert len(snap_none.positions) == 0
    assert len(snap_none.active_orders) == 0

    print("\n[SUCCESS] Live Filter Verification Passed.")

if __name__ == "__main__":
    test_live_portfolio_filter()
