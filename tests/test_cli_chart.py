import pytest
import json
from unittest.mock import MagicMock, patch
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta

def test_cli_chart_success():
    """Tests 'chart' command."""
    mock_trade = MagicMock()
    import datetime
    mock_bar = MagicMock()
    mock_bar.timestamp = datetime.datetime.fromtimestamp(1600000000)
    mock_bar.close = 150.0
    mock_trade.get_chart.return_value = [mock_bar]
    
    with patch("py_captrader.services.has_broker", return_value=True), \
         patch("py_captrader.services.get_broker", return_value=MagicMock()), \
         patch("py_tradeobject.core.TradeObject.get_or_create", return_value=mock_trade):
        
        controller = CLIController(mode=CLIMode.BOT)
        response_json = controller.process_input("chart AAPL")
        res = json.loads(response_json)
        
        assert res["success"] is True
        assert len(res["payload"]["data"]) == 1
        assert res["payload"]["ticker"] == "AAPL"
