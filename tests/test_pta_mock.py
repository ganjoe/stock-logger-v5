import sys
import os
from py_captrader import services
from py_cli.controller import CLIController, CLIMode
from py_cli.models import CLIContext
from py_tradeobject.interface import IBrokerAdapter, BrokerUpdate
from typing import Dict, List, Any

# Mock Broker implementation
class MockBroker(IBrokerAdapter):
    def __init__(self):
        self.orders = {
            101: ("AAPL", "SELL", 50, 180.0, "TRD-AAPL-1"),
            102: ("INTC", "BUY", 100, 25.0, "TRD-INTC-1")
        }

    def get_account_summary(self) -> Dict[str, float]:
        return {"NetLiquidation": 100000.0, "TotalCashValue": 25000.0}
    
    def get_positions(self) -> List[Any]:
        class MockContract:
            def __init__(self, symbol): self.symbol = symbol
        class MockPos:
            def __init__(self, symbol, position, avgCost):
                self.contract = MockContract(symbol)
                self.position = position
                self.avgCost = avgCost
        return [MockPos("AAPL", 50, 150.0), MockPos("INTC", 100, 30.0)]

    def get_all_open_orders(self) -> List[Any]:
        class MockOrder:
            def __init__(self, orderId, action, totalQuantity, lmtPrice, orderRef):
                self.orderId = orderId
                self.action = action
                self.totalQuantity = totalQuantity
                self.lmtPrice = lmtPrice
                self.auxPrice = 0.0
                self.orderType = "LMT"
                self.orderRef = orderRef

        class MockTrade:
            def __init__(self, symbol, orderId, action, qty, price, ref):
                self.contract = type('obj', (object,), {'symbol': symbol})
                self.order = MockOrder(orderId, action, qty, price, ref)

        return [
            MockTrade(sym, oid, act, qty, prc, ref)
            for oid, (sym, act, qty, prc, ref) in self.orders.items()
        ]

    def get_current_price(self, symbol: str) -> float: return 175.0
    def place_order(self, **kwargs): return "MOCK_OID"
    
    def cancel_order(self, orderId):
        if int(orderId) in self.orders:
            del self.orders[int(orderId)]
            return True
        return False
    def get_updates(self, *args): return BrokerUpdate([], [], [])
    def get_historical_data(self, *args): return []

def run_pta_test(message: str):
    # Setup
    broker = MockBroker()
    services.register_broker(broker)
    
    # Create Mock Trade File so TradeObject can load it
    mock_trade_dir = "./data/trades/AAPL"
    os.makedirs(mock_trade_dir, exist_ok=True)
    mock_trade_path = os.path.join(mock_trade_dir, "TRD-AAPL-1.json")
    with open(mock_trade_path, "w") as f:
        json.dump({
            "ticker": "AAPL",
            "id": "TRD-AAPL-1",
            "status": "OPEN",
            "current_quantity": 50,
            "average_price": 150.0,
            "orders": {
                "101": {"orderId": "101", "action": "SELL", "totalQuantity": 50, "lmtPrice": 180.0, "status": "SUBMITTED"}
            }
        }, f)

    # Import handlers
    import py_cli.handlers_monitor
    import py_cli.handlers_execution
    import py_cli.handlers_trade
    import py_cli.handlers_pta
    
    # Create controller
    controller = CLIController(mode=CLIMode.BOT)
    services.register_cli(controller)
    
    print(f"--- PTA TEST START ---")
    print(f"User: {message}")
    
    # Process
    resp = controller.process_input(f"pta {message}")
    print(f"\nPTA Response:\n{resp}")
    print(f"--- PTA TEST END ---")

if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "lösche apple orders"
    run_pta_test(msg)
