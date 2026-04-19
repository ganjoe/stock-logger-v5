import pytest
import json
from unittest.mock import MagicMock, patch
from py_cli.controller import CLIController
from py_cli.models import CLIMode
import py_cli.handlers_monitor, py_cli.handlers_trade, py_cli.handlers_analytics, py_cli.handlers_connection, py_cli.handlers_execution, py_cli.handlers_history, py_cli.handlers_pta

def test_cli_wizard_mock():
    """Tests 'wizard' command."""
    mock_result = MagicMock()
    mock_result.shares = 100
    
    with patch("py_riskmanager.minervini.MinerviniSizer.calculate_sizing", return_value=mock_result), \
         patch("dataclasses.asdict", return_value={"shares": 100}):
        
        controller = CLIController(mode=CLIMode.BOT)
        res = json.loads(controller.process_input('wizard {"symbol": "AAPL", "entry": 150.0, "stop": 140.0}'))
        assert res["success"] is True
        assert res["payload"]["shares"] == 100
