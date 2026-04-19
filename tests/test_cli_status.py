import pytest
import json
from unittest.mock import MagicMock, patch
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta
from py_captrader import services
from py_tradeobject.interface import IBrokerAdapter

class MockPosition:
    def __init__(self, symbol, qty, avg_cost):
        self.contract = MagicMock()
        self.contract.symbol = symbol
        self.position = qty
        self.avgCost = avg_cost

def test_cli_status_no_connection():
    """Tests 'status' command when no broker is connected."""
    with patch("py_captrader.services.has_broker", return_value=False):
        controller = CLIController(mode=CLIMode.BOT)
        response_json = controller.process_input("status")
        res = json.loads(response_json)
        
        assert res["success"] is False
        assert res["error_code"] == "NO_CONNECTION"

def test_cli_status_with_mock_data():
    """Tests 'status' command with mocked broker data."""
    mock_broker = MagicMock(spec=IBrokerAdapter)
    mock_broker.get_account_summary.return_value = {"TotalCashValue": 10000.0, "NetLiquidation": 15000.0}
    mock_broker.get_positions.return_value = [
        MockPosition("AAPL", 10, 150.0),
        MockPosition("MSFT", 5, 300.0)
    ]
    mock_broker.get_all_open_orders.return_value = []
    mock_broker.get_current_price.return_value = 160.0

    with patch("py_captrader.services.has_broker", return_value=True), \
         patch("py_captrader.services.get_broker", return_value=mock_broker), \
         patch("py_portfolio_state.live.LivePortfolioManager.save_snapshot"):
        
        controller = CLIController(mode=CLIMode.BOT)
        
        # Test Full Status
        res_full = json.loads(controller.process_input("status"))
        assert res_full["success"] is True
        assert len(res_full["payload"]["positions"]) == 2
        
        # Test Filtered Status
        res_filtered = json.loads(controller.process_input('status {"ticker": "AAPL"}'))
        assert res_filtered["success"] is True
        assert len(res_filtered["payload"]["positions"]) == 1
        assert res_filtered["payload"]["positions"][0]["ticker"] == "AAPL"
