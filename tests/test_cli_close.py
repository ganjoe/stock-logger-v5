import pytest
import json
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta

def test_cli_close_safety():
    """Tests 'close' command safety locks."""
    controller = CLIController(mode=CLIMode.BOT)
    
    # Test without force/confirm (should fail in BOT mode)
    response_json = controller.process_input("close TRD-123")
    res = json.loads(response_json)
    assert res["success"] is False
    assert res["error_code"] == "SAFETY_LOCK"
    
    # Test with force
    response_json = controller.process_input("close TRD-123 --force")
    res = json.loads(response_json)
    assert res["success"] is True
    assert res["payload"]["trade_id"] == "TRD-123"
