"""
py_cli/handlers_monitor.py
Implementation of Monitoring Commands (status, trades).
"""
from typing import List, Dict, Any
from .models import CLIContext, CommandResponse
from .commands import ICommand, registry
# Note: In a real scenario, we would inject the TradeManager/Broker here.
# For now, we'll mock the data fetching or use placeholders.
# We should probably have a 'ServiceLocator' or import a singleton 'system'.

class StatusCommand(ICommand):
    name = "status"
    description = "Displays the current portfolio snapshot and risk metrics."
    syntax = "status"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        # TODO: Connect to real py_financial_math / Broker
        # For prototype, return dummy data structure that fits the requirement
        
        # Mock Data matching F-DAT-010 (Trade Identity Reconciliation)
        data = {
            "equity": 10000.0,
            "cash": 8000.0,
            "pnl_unrealized": 500.0,
            "risk_heat": 2.5, # %
            "positions": [
                {"trade_id": "fc3f41e5", "ticker": "GOOGL", "qty": 10, "pnl": 50.0}
            ]
        }
        
        if ctx.mode.value == "BOT":
            return CommandResponse(True, "Status valid", data)
        
        # Human Format
        msg = (
            f"--- PORTFOLIO STATUS ---\n"
            f"Equity: ${data['equity']:.2f} | Cash: ${data['cash']:.2f}\n"
            f"Heat:   {data['risk_heat']}% | PnL: ${data['pnl_unrealized']:.2f}"
        )
        return CommandResponse(True, msg, data)

class TradesCommand(ICommand):
    name = "trades"
    description = "Lists all open positions with ID-First display."
    syntax = "trades"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        # Mock List
        trades = [
            {"id": "fc3f41e5...", "ticker": "GOOGL", "qty": 10, "entry": 150.0},
            {"id": "a1b2c3d4...", "ticker": "MSFT", "qty": 5, "entry": 300.0}
        ]
        
        if ctx.mode.value == "BOT":
            return CommandResponse(True, "Trades list", {"trades": trades})
            
        # Human Table (ID First!)
        lines = ["ID               | Ticker | Qty | Entry"]
        lines.append("-" * 40)
        for t in trades:
            lines.append(f"{t['id']:<16} | {t['ticker']:<6} | {t['qty']:<3} | {t['entry']}")
            
        return CommandResponse(True, "\n".join(lines), {"trades": trades})

# Registration
registry.register(StatusCommand())
registry.register(TradesCommand())
