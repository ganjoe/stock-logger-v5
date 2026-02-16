# tests/test_cli_api.py
import sys
import os
import json
# import pytest
from unittest.mock import MagicMock

# Adjust path to find modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from py_cli.controller import CLIController
from py_cli.models import CLIMode
from py_cli.commands import ICommand, registry
import py_cli.handlers_execution
import py_cli.handlers_monitor

# Wir benötigen KEINEN Broker, da wir Mocks nutzen oder den Service Locator manipulieren

from py_captrader import services
from py_tradeobject.interface import IBrokerAdapter
from py_portfolio_state.objects import PortfolioSnapshot

# --- Mocks ---
class MockBroker(IBrokerAdapter):
    # Abstract methods from IBrokerAdapter
    def get_account_summary(self): return {"NetLiquidation": 50000.0}
    def get_positions(self): return []
    def get_all_open_orders(self): return []
    def get_current_price(self, symbol): return 100.0
    def place_order(self, *args, **kwargs): return "MOCK_OID"
    def cancel_order(self, *args): return True
    def get_updates(self, *args): 
        from py_tradeobject.interface import BrokerUpdate
        return BrokerUpdate([], [], [])
    def get_historical_data(self, *args): return []

# --- Contexts ---
def get_bot_controller():
    # Register Mock Broker
    services.register_broker(MockBroker())
    return CLIController(mode=CLIMode.BOT)

# --- Tests ---



def test_status_command_bot():
    print("Testing Status Command (BOT)...")
    cli = get_bot_controller()
    resp_json = cli.process_input("status")
    resp = json.loads(resp_json)
    
    assert resp["success"] is True
    assert resp["payload"]["equity"] == 50000.0
    assert resp["message"] == "Live Portfolio Snapshot"
    print("✅ Status Command (BOT) Passed.")

# def test_trade_command_bot(cli_controller):
#     # TODO: Implement handlers_trade.py first
#     pass

if __name__ == "__main__":
    try:

        test_status_command_bot()
        print("\n[SUCCESS] CLI API Verification PASSED")
    except Exception as e:
        print(f"\n[FAILURE] CLI API Verification FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
