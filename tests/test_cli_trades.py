import pytest
import json
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta

def test_cli_trades_mock():
    """Tests 'trades' command (mostly returning mock data currently)."""
    controller = CLIController(mode=CLIMode.BOT)
    response_json = controller.process_input("trades")
    res = json.loads(response_json)
    
    assert res["success"] is True
    assert "trades" in res["payload"]
    assert len(res["payload"]["trades"]) > 0
