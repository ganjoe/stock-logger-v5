import pytest
import json
from unittest.mock import MagicMock, patch
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta
from py_captrader import services

def test_cli_pta_basic():
    """Tests the 'pta' command with a mocked bridge."""
    mock_bridge = MagicMock()
    mock_bridge.chat.return_value = "This is a mock PTA response."
    
    with patch("py_cli.handlers_pta._bridge", mock_bridge):
        controller = CLIController(mode=CLIMode.BOT)
        response_json = controller.process_input("pta 'hello bot'")
        res = json.loads(response_json)
        
        assert res["success"] is True
        assert res["message"] == "This is a mock PTA response."
        mock_bridge.chat.assert_called_once_with("'hello bot'")

def test_cli_pta_no_args():
    """Tests 'pta' command with no arguments."""
    controller = CLIController(mode=CLIMode.BOT)
    response_json = controller.process_input("pta")
    res = json.loads(response_json)
    
    assert res["success"] is False
    assert "Bitte gib eine Anweisung" in res["message"]
