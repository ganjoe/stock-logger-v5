import pytest
import json
from unittest.mock import MagicMock, patch
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta
from py_captrader import services

def test_cli_quote_success():
    """Tests 'quote' command with a successful price fetch."""
    mock_broker = MagicMock()
    mock_broker.get_current_price.return_value = 175.50
    
    # We also need to mock TradeObject or let it use the mock_broker
    # handlers_monitor.py uses TradeObject.get_or_create
    mock_trade = MagicMock()
    mock_trade.get_quote.return_value = 175.50
    
    with patch("py_captrader.services.has_broker", return_value=True), \
         patch("py_captrader.services.get_broker", return_value=mock_broker), \
         patch("py_tradeobject.core.TradeObject.get_or_create", return_value=mock_trade):
        
        controller = CLIController(mode=CLIMode.BOT)
        response_json = controller.process_input("quote AAPL")
        res = json.loads(response_json)
        
        assert res["success"] is True
        assert res["payload"]["price"] == 175.50
        assert "AAPL" in res["message"]

def test_cli_quote_no_args():
    """Tests 'quote' command with missing ticker."""
    controller = CLIController(mode=CLIMode.BOT)
    response_json = controller.process_input("quote")
    res = json.loads(response_json)
    
    assert res["success"] is False
    assert res["error_code"] == "INVALID_ARGS"
