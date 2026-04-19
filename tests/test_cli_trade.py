import pytest
import json
from unittest.mock import MagicMock, patch
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta
from py_captrader import services

def test_cli_trade_cash():
    """Tests the 'trade' command with action 'CASH'."""
    controller = CLIController(mode=CLIMode.BOT)
    
    # Deposit
    response_json = controller.process_input('trade {"action": "CASH", "quantity": 1000}')
    res = json.loads(response_json)
    assert res["success"] is True
    assert res["payload"]["amount"] == 1000.0
    
    # Withdrawal
    response_json = controller.process_input('trade {"action": "CASH", "quantity": -500}')
    res = json.loads(response_json)
    assert res["success"] is True
    assert res["payload"]["amount"] == -500.0

def test_cli_trade_enter_mock():
    """Tests the 'trade ENTER' command logic."""
    mock_trade = MagicMock()
    mock_trade.id = "MOCK-TRD-1"
    mock_trade.status.value = "OPEN"
    mock_trade.enter.return_value = "ORDER-101"
    
    with patch("py_captrader.services.has_broker", return_value=True), \
         patch("py_captrader.services.get_broker", return_value=MagicMock()), \
         patch("py_cli.handlers_trade.TradeObject", return_value=mock_trade):
        
        controller = CLIController(mode=CLIMode.BOT)
        payload = 'trade {"action": "ENTER", "ticker": "AAPL", "quantity": 10, "limit_price": 150.0}'
        response_json = controller.process_input(payload)
        res = json.loads(response_json)
        
        assert res["success"] is True
        assert res["payload"]["trade_id"] == "MOCK-TRD-1"
        assert res["payload"]["broker_order_id"] == "ORDER-101"
