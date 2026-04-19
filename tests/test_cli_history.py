import pytest
import json
from unittest.mock import MagicMock, patch
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta

def test_cli_history_mock():
    """Tests 'history' command."""
    mock_snap = MagicMock()
    mock_snap.to_dict.return_value = {"date": "2023-01-01", "positions": []}
    
    with patch("py_portfolio_state.history.HistoryFactory.load_all_trades"), \
         patch("py_portfolio_state.history.HistoryFactory.get_snapshot_at", return_value=mock_snap):
        
        controller = CLIController(mode=CLIMode.BOT)
        res = json.loads(controller.process_input("history 5"))
        
        assert res["success"] is True
        assert res["payload"]["date"] == "2023-01-01"
