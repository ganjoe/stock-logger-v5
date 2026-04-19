import pytest
import json
from unittest.mock import patch
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta

def test_cli_bulk_fetch():
    """Tests 'bulk_fetch' command."""
    with patch("subprocess.Popen") as mock_popen:
        controller = CLIController(mode=CLIMode.BOT)
        res = json.loads(controller.process_input("bulk_fetch 123"))
        assert res["success"] is True
        assert "Bulk fetch started" in res["message"]
        mock_popen.assert_called_once()
