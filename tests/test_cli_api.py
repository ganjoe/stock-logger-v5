# tests/test_cli_api.py
import sys
import os
import json
import pytest
from unittest.mock import MagicMock

# Adjust path to find modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from py_cli.controller import CLIController
from py_cli.models import CLIMode
from py_cli.commands import ICommand, registry
import py_cli.handlers_execution
import py_cli.handlers_monitor
import py_cli.handlers_user_mode
# Wir benötigen KEINEN Broker, da wir Mocks nutzen oder den Service Locator manipulieren

from py_captrader import services
from py_tradeobject.interface import IBrokerAdapter
from py_portfolio_state.objects import PortfolioSnapshot

# --- Mocks ---
class MockBroker(IBrokerAdapter):
    def get_account_summary(self): return {"NetLiquidation": 50000.0}
    def get_positions(self): return []
    def get_all_open_orders(self): return []
    def get_current_price(self, symbol): return 100.0

@pytest.fixture
def cli_controller():
    # Register Mock Broker
    services.register_broker(MockBroker())
    return CLIController(mode=CLIMode.BOT)

@pytest.fixture
def cli_human_controller():
    # Human controller uses same registry but renders text
    services.register_broker(MockBroker())
    return CLIController(mode=CLIMode.HUMAN)

# --- Tests ---

def test_user_mode_switching(cli_controller):
    # 1. Check Initial Mode (Controller initialized as BOT)
    assert cli_controller.context.mode == CLIMode.BOT
    
    # 2. Switch to Human
    resp_json = cli_controller.process_input("user human")
    resp = json.loads(resp_json)
    
    assert resp["success"] is True
    assert resp["payload"]["mode"] == "HUMAN"
    # Note: Controller instance stays same, but Context changed
    assert cli_controller.context.mode == CLIMode.HUMAN
    
    # 3. Switch back to PTA (Bot) - Output should be JSON again?
    # Wait, if context is HUMAN, process_input renders Text.
    # So next command output will be Text.
    # We call "user pta" -> Context switches to BOT -> Render returns JSON.
    # Let's verify this dynamic switch behavior.
    
    resp_text = cli_controller.process_input("user pta")
    # This should be JSON string because mode switched inside execution, 
    # and _render_response checks context.mode at the end.
    
    print(f"DEBUG Output: {resp_text}")
    try:
        resp2 = json.loads(resp_text)
        assert resp2["success"] is True
        assert resp2["payload"]["mode"] == "BOT"
    except json.JSONDecodeError:
        pytest.fail("Switching to PTA did not result in JSON output")

def test_status_command_bot(cli_controller):
    # Status command should use the MockBroker we registered
    resp_json = cli_controller.process_input("status")
    resp = json.loads(resp_json)
    
    assert resp["success"] is True
    assert resp["payload"]["equity"] == 50000.0
    assert resp["message"] == "Live Portfolio Snapshot"

# def test_trade_command_bot(cli_controller):
#     # TODO: Implement handlers_trade.py first
#     pass
