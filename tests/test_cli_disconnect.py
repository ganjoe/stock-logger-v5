import pytest
import json
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta
from py_captrader import session

def test_cli_disconnect():
    """Tests 'disconnect' command."""
    controller = CLIController(mode=CLIMode.BOT)
    
    # Ensure we are disconnected first (or mock it)
    session.disconnect()
    
    response_json = controller.process_input("disconnect")
    res = json.loads(response_json)
    
    assert res["success"] is True
    assert "disconnected" in res["message"].lower()
    assert not session.is_connected()
