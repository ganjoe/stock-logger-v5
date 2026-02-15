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

import json
from py_captrader import services
from py_portfolio_state.live import LivePortfolioManager

class StatusCommand(ICommand):
    name = "status"
    description = "Displays the current portfolio snapshot (Live Dump)."
    syntax = "status"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        try:
            # 1. Parse JSON Filter (Optional)
            ticker_filter = None
            if args:
                raw_json = " ".join(args)
                try:
                    payload = json.loads(raw_json)
                    ticker_filter = payload.get("ticker")
                except json.JSONDecodeError:
                    # If not JSON, maybe it's a raw ticker string? 
                    # For Bot-First/JSON policy, we should error or try to be smart.
                    # Let's be smart for human use: if it's one word, treat as ticker.
                    if len(args) == 1 and not args[0].startswith("{"):
                        ticker_filter = args[0]
                    else:
                        return CommandResponse(False, message="Invalid JSON filter format.", error_code="JSON_ERROR")

            # 2. Get Live Broker & Manager
            if not services.has_broker():
                return CommandResponse(False, message="No Active Broker Connection.", error_code="NO_CONNECTION")
                
            broker = services.get_broker()
            manager = LivePortfolioManager(broker)
            
            # 3. Fetch Snapshot
            print("  [CLI] Fetching Live Snapshot...")
            snap = manager.snapshot(ticker=ticker_filter)
            
            # 4. Dump Data
            data_dict = snap.to_dict()
            msg = f"Live Snapshot (Filtered: {ticker_filter})" if ticker_filter else "Live Portfolio Snapshot"
            return CommandResponse(True, payload=data_dict, message=msg)
            
        except Exception as e:
            return CommandResponse(False, payload=None, message=f"Error: {e}", error_code="FETCH_ERROR")

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
