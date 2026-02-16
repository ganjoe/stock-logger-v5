# py_cli/handlers_analytics.py
import json
from typing import List, Dict, Any
from .models import CLIContext, CommandResponse, CLIMode
from .commands import ICommand, registry
from py_analytics.capture import SnapshotAnalyzer
from py_analytics.series import SeriesAnalyzer
from py_portfolio_state.live import LivePortfolioManager
from py_portfolio_state.history import HistoryFactory
from py_captrader import services

class AnalyzeCommand(ICommand):
    name = "analyze"
    description = "Runs analytics on live or historical data."
    syntax = "analyze [live|history] [json_payload]"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        if not args:
            return CommandResponse(False, "Usage: analyze [live|history] [json_filter]", error_code="INVALID_ARGS")

        sub_cmd = args[0].lower()
        payload = {}
        if len(args) > 1:
            try:
                payload = json.loads(" ".join(args[1:]))
            except json.JSONDecodeError:
                # If not JSON, check if it's just a ticker string for 'live'
                if sub_cmd == "live":
                    payload = {"ticker": args[1]}
                else:
                    return CommandResponse(False, "Invalid JSON payload.", error_code="JSON_ERROR")

        if sub_cmd == "live":
            return self._handle_live(payload)
        elif sub_cmd == "history":
            return self._handle_history(payload)
        else:
            return CommandResponse(False, f"Unknown sub-command: {sub_cmd}", error_code="UNKNOWN_SUBCOMMAND")

    def _handle_live(self, p: Dict[str, Any]) -> CommandResponse:
        if not services.has_broker():
            return CommandResponse(False, "No Active Broker Connection.", error_code="NO_CONNECTION")
        
        broker = services.get_broker()
        manager = LivePortfolioManager(broker)
        ticker = p.get("ticker")
        
        # 1. Capture Snapshot (Filtered if ticker provided)
        snap = manager.snapshot(ticker=ticker)
        
        # 2. Analyze
        analyzer = SnapshotAnalyzer()
        report = analyzer.analyze(snap)
        
        return CommandResponse(True, payload=report.to_dict(), message=f"Live Analytics Report (Ticker: {ticker or 'ALL'})")

    def _handle_history(self, p: Dict[str, Any]) -> CommandResponse:
        days = p.get("days", 30)
        ticker = p.get("ticker")
        
        # 1. Setup Factory
        factory = HistoryFactory(trades_dir="./data/trades")
        factory.load_all_trades()
        
        # 2. Get Series of Snapshots
        # Note: In a real scenario we'd query a DB or a list of saved daily files.
        # For now, we simulate by fetching the last N days if available.
        snapshots = [] # Implementation of bulk history fetch needed in Factory?
        # Placeholder: SeriesAnalyzer needs a list.
        # Since we just implemented it, we assume we have a way to get the list.
        # Let's keep it minimal for now as proof of concept.
        
        analyzer = SeriesAnalyzer()
        # report = analyzer.analyze(snapshots) 
        
        return CommandResponse(False, "History Analytics not yet fully linked to storage.", error_code="NOT_IMPLEMENTED")


# py_cli/handlers_analytics.py

class BulkFetchCommand(ICommand):
    name = "bulk_fetch"
    description = "Triggers background bulk data fetch."
    syntax = "bulk_fetch [client_id]"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        import subprocess
        
        client_id = 999
        if args:
            try:
                client_id = int(args[0])
            except ValueError:
                pass
                
        # Launch script in background
        # We use Popen to not block the PTA
        cmd = [sys.executable, "py_market_data/bulk_fetch.py", "--client-id", str(client_id)]
        
        try:
            # nohup-like behavior not strictly needed if we don't wait?
            # actually Popen returns immediately.
            subprocess.Popen(cmd, start_new_session=True)
            return CommandResponse(True, message=f"Bulk fetch started (Client {client_id}) in background.")
        except Exception as e:
            return CommandResponse(False, message=f"Failed to start bulk fetch: {e}")

# Register
registry.register(AnalyzeCommand())
registry.register(BulkFetchCommand())
