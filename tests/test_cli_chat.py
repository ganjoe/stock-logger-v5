import pytest
import json
from unittest.mock import patch, MagicMock
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta

def test_cli_chat_exit():
    """Tests 'chat' command (ensuring it can start and exit)."""
    # We mock 'input' to return 'exit' immediately
    with patch("builtins.input", side_effect=["exit"]), \
         patch("py_cli.handlers_pta.PTABridge"), \
         patch("py_captrader.services.get_cli"):
        
        controller = CLIController(mode=CLIMode.BOT)
        # Note: Chat command in BOT mode still enters the loop in current implementation
        # might be a bug in business logic but here we test the registration.
        res = json.loads(controller.process_input("chat"))
        
        assert res["success"] is True
        assert "beendet" in res["message"]
