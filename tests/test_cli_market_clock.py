import pytest
import json
from unittest.mock import patch
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta

def test_cli_market_clock():
    """Tests 'market_clock' command."""
    mock_status = {"status": "OPEN", "next_event": "CLOSE"}
    with patch("py_market_data.market_clock.MarketClock.get_status", return_value=mock_status):
        controller = CLIController(mode=CLIMode.BOT)
        res = json.loads(controller.process_input("market_clock"))
        assert res["success"] is True
        assert res["payload"]["status"] == "OPEN"
