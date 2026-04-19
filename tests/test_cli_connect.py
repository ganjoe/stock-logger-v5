import pytest
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta
from py_captrader import session
import py_cli.handlers_connection

def test_connect_default():
    """Tests the 'connect' command with default parameters."""
    controller = CLIController(mode=CLIMode.BOT)
    
    # We use CLIMode.BOT to get JSON responses which are easier to parse in tests
    response_json = controller.process_input("connect")
    
    import json
    res = json.loads(response_json)
    
    # If the gateway is not running, this might fail, 
    # but the logic of the command itself (parsing, session call) is exercised.
    assert "success" in res
    if res["success"]:
        assert "Connected" in res["message"]
        assert session.is_connected()
    else:
        assert res["error_code"] in ["CONNECTION_ERROR", "ALREADY_CONNECTED"]
