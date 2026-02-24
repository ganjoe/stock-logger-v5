# py_cli/handlers_analytics.py
import json
import sys
from typing import List, Dict, Any
from .models import CLIContext, CommandResponse, CLIMode
from .commands import ICommand, registry
from py_riskmanager.analytics import SnapshotAnalyzer, SeriesAnalyzer
from py_portfolio_state.live import LivePortfolioManager
from py_portfolio_state.history import HistoryFactory
from py_tradeobject.core import TradeObject
from py_captrader import services
from py_market_data.market_clock import MarketClock
from py_riskmanager.minervini import MinerviniSizer, TradeParameters, SizingContext

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
        to_dashboard = p.get("to_dashboard", False)
        
        from datetime import datetime, timedelta
        from py_riskmanager.analytics import PerformanceAnalyzer
        
        end = datetime.now()
        start = end - timedelta(days=days)
        
        # 1. Load all trades
        factory = HistoryFactory(trades_dir="./data/trades")
        factory.load_all_trades()
        
        # 2. Get closed trades in window
        closed = factory.get_closed_trades(start, end)
        
        # Filter by ticker if requested
        if ticker:
            closed = [t for t in closed if t.ticker.upper() == ticker.upper()]
        
        if not closed:
            return CommandResponse(True, message=f"No closed trades in the last {days} days.", payload={
                "period_days": days,
                "total_trades": 0
            })
        
        # 3. Analyze performance
        analyzer = PerformanceAnalyzer()
        metrics = analyzer.analyze_trades(closed)
        
        # 4. Build trade list (sorted by PnL descending)
        sorted_trades = sorted(closed, key=lambda t: t.pnl_absolute, reverse=True)
        trade_list = []
        for t in sorted_trades:
            trade_list.append({
                "ticker": t.ticker,
                "direction": t.direction,
                "entry": t.entry_date.strftime("%Y-%m-%d"),
                "exit": t.exit_date.strftime("%Y-%m-%d"),
                "pnl": round(t.pnl_absolute, 2),
                "duration_days": t.duration_days
            })
        
        # 5. Summary
        total_pnl = sum(t.pnl_absolute for t in closed)
        payload = {
            "period_days": days,
            "total_pnl": round(total_pnl, 2),
            "metrics": metrics,
            "trades": trade_list
        }
        
        # 6. Optional: Pipe equity curve to dashboard
        if to_dashboard:
            try:
                snapshots = factory.get_daily_snapshots(start, end)
                curve = [{"t": s.timestamp.isoformat(), "v": s.equity} for s in snapshots]
                
                import requests
                url = "http://localhost:8000/broadcast"
                push_payload = {
                    "msg_type": "CHART_UPDATE",
                    "payload_type": "PNL",
                    "data": curve
                }
                requests.post(url, json=push_payload, timeout=2)
                return CommandResponse(True, message=f"PnL Curve ({days}d) piped to Dashboard. Total PnL: {total_pnl:+.2f}", payload={"status": "PIPED", "total_pnl": round(total_pnl, 2)})
            except Exception as e:
                return CommandResponse(False, message=f"Dashboard piping failed: {e}. Use without to_dashboard.", error_code="PIPE_ERROR")

        return CommandResponse(True, payload=payload, message=f"History Report ({days}d): {len(closed)} trades, PnL: {total_pnl:+.2f}")


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

class MarketClockCommand(ICommand):
    name = "market_clock"
    description = "Returns current market status and time to next event."
    syntax = "market_clock"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        status = MarketClock.get_status()
        return CommandResponse(True, payload=status, message=f"Market Status: {status['status']}")

class WizardCommand(ICommand):
    name = "wizard"
    description = "Calculates Minervini Position Sizing based on parameters."
    syntax = "wizard <json_payload>"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        if not args:
            return CommandResponse(False, "Usage: wizard <json_payload>", error_code="INVALID_ARGS")

        try:
            payload = json.loads(" ".join(args))
        except json.JSONDecodeError:
             return CommandResponse(False, "Invalid JSON payload.", error_code="JSON_ERROR")
             
        # Extraction
        symbol = payload.get("symbol", "UNKNOWN")
        entry = payload.get("entry", 0.0)
        stop = payload.get("stop", 0.0)
        risk_pct = payload.get("risk_pct", 1.0)
        max_pos_pct = payload.get("max_pos_pct", 25.0)
        
        # Auto-fetch Entry Price if missing (0.0) and Broker available
        if entry <= 0.0:
            if services.has_broker():
                try:
                    broker = services.get_broker()
                    # User Request: Use TradeObject interface for price query
                    # And ensure trade is created/persisted! (get_or_create)
                    temp_trade = TradeObject.get_or_create(ticker=symbol, broker=broker)
                    fetched_price = temp_trade.get_quote()
                    
                    if fetched_price > 0:
                        entry = fetched_price
                    else:
                        return CommandResponse(False, f"Fetched price for {symbol} is invalid/zero.", error_code="PRICE_ERROR")
                except Exception as e:
                    return CommandResponse(False, f"Could not fetch live price for {symbol}: {e}", error_code="PRICE_FETCH_FAILED")
            else:
                return CommandResponse(False, "Entry price is zero and no broker connection to fetch it.", error_code="MISSING_DATA")

        # Context (Equity/Cash)
        equity = payload.get("equity_override")
        cash = payload.get("exposure_override") # User map this to Buying Power/Cash? Let's assume available cash.
        
        # If no override, try to get from Broker
        if equity is None or cash is None:
            if services.has_broker():
                try:
                    broker = services.get_broker()
                    # Optimized: Use get_account_summary directly
                    summary = broker.get_account_summary()
                    
                    if equity is None: equity = summary.get('NetLiquidation', 0.0)
                    if cash is None: cash = summary.get('TotalCashValue', 0.0)
                except Exception:
                    pass
            
            # Fallback if still None
            if equity is None: equity = 100000.0 
            if cash is None: cash = 100000.0
            
        # Sizing
        sizer = MinerviniSizer()
        ctx_obj = SizingContext(total_equity=float(equity), available_cash=float(cash), current_exposure=0.0)
        params = TradeParameters(symbol=symbol, entry_price=float(entry), stop_loss=float(stop), risk_pct=float(risk_pct), max_pos_pct=float(max_pos_pct))
        
        result = sizer.calculate_sizing(ctx_obj, params)
        
        # Convert dataclass to dict for JSON response
        from dataclasses import asdict
        return CommandResponse(True, payload=asdict(result), message=f"Wizard Result for {symbol}")

# Register
registry.register(AnalyzeCommand())
registry.register(BulkFetchCommand())
registry.register(MarketClockCommand())
registry.register(WizardCommand())
