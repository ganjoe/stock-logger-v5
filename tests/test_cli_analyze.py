import pytest
import json
from unittest.mock import MagicMock, patch
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta
from py_captrader import services
import py_cli.handlers_pta
import py_cli.handlers_analytics

def test_cli_analyze_live_no_conn():
    """Tests 'analyze live' without connection."""
    with patch("py_captrader.services.has_broker", return_value=False):
        controller = CLIController(mode=CLIMode.BOT)
        res = json.loads(controller.process_input("analyze live"))
        assert res["success"] is False
        assert res["error_code"] == "NO_CONNECTION"

def test_cli_analyze_history():
    """Tests 'analyze history'."""
    # We mock PerformanceAnalyzer and HistoryFactory
    mock_metrics = {"winrate": 0.6, "profit_factor": 1.5}
    
    with patch("py_riskmanager.analytics.PerformanceAnalyzer.analyze_trades", return_value=mock_metrics), \
         patch("py_portfolio_state.history.HistoryFactory.load_all_trades"), \
         patch("py_portfolio_state.history.HistoryFactory.get_closed_trades", return_value=[]):
        
        controller = CLIController(mode=CLIMode.BOT)
        res = json.loads(controller.process_input('analyze history {"days": 30}'))
        
        assert res["success"] is True
        assert "No closed trades" in res["message"] 
