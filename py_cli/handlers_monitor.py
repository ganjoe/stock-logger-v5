import json
import sys
from typing import List, Dict, Any
from .models import CLIContext, CommandResponse
from .commands import ICommand, registry
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

class QuoteCommand(ICommand):
    name = "quote"
    description = "Fetches the current market price for a symbol."
    syntax = "quote SYMBOL"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        if not args:
            return CommandResponse(False, message="Usage: quote SYMBOL", error_code="INVALID_ARGS")
            
        ticker = args[0].upper()
        
        if not services.has_broker():
            return CommandResponse(False, message="No Active Broker Connection.", error_code="NO_CONNECTION")
            
        try:
            broker = services.get_broker()
            print(f"  [CLI] Fetching Quote for {ticker} (via Persistent TradeObject)...")
            
            # Use TradeObject factory
            from py_tradeobject.core import TradeObject
            
            # Retrieves latest active trade OR creates new PLANNED one (persisted)
            trade = TradeObject.get_or_create(ticker, broker)
            
            # Fetch Price (and update internal state if we map it later)
            price = trade.get_quote()
            
            # Optionally save again if get_quote modified internal state (it currently doesn't, but good practice)
            trade.save()
            
            return CommandResponse(
                True, 
                message=f"Quote {ticker}: {price}", 
                payload={"ticker": ticker, "price": price}
            )
        except Exception as e:
            return CommandResponse(False, message=f"Quote Error: {str(e)}", error_code="QUOTE_ERROR")

class ChartCommand(ICommand):
    name = "chart"
    description = "Fetches historical chart data for a symbol."
    syntax = "chart SYMBOL [JSON_PAYLOAD]"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        if not args:
            return CommandResponse(False, message="Usage: chart SYMBOL [--to-dashboard] [JSON_PAYLOAD]", error_code="INVALID_ARGS")
            
        ticker = args[0].upper()
        
        # Check for piping flag
        to_dashboard = "--to-dashboard" in args
        clean_args = [a for a in args[1:] if a != "--to-dashboard"]
        
        payload = {}
        if clean_args:
            try:
                payload = json.loads(" ".join(clean_args))
            except json.JSONDecodeError:
                pass 

        timeframe = payload.get("timeframe", "1D")
        lookback = payload.get("lookback", "1Y")

        if not services.has_broker():
            return CommandResponse(False, message="No Active Broker Connection.", error_code="NO_CONNECTION")
            
        try:
            broker = services.get_broker()
            from py_tradeobject.core import TradeObject
            from py_market_data.storage import normalize_timestamp
            trade = TradeObject.get_or_create(ticker, broker)
            
            bars = trade.get_chart(timeframe=timeframe, lookback=lookback)
            data = [{"t": normalize_timestamp(b.timestamp, timeframe), "v": float(b.close)} for b in bars]
            
            if to_dashboard:
                # PIPE DATA DIRECTLY (Prevents LLM Context Bloat)
                import requests
                url = "http://localhost:8000/broadcast"
                push_payload = {
                    "msg_type": "CHART_UPDATE",
                    "payload_type": "PRICE",
                    "data": data
                }
                try:
                    requests.post(url, json=push_payload, timeout=2)
                    return CommandResponse(
                        True, 
                        message=f"Chart for {ticker} direct-piped to Dashboard ({len(data)} bars).",
                        payload={"status": "PIPED", "count": len(data)} # Small payload
                    )
                except Exception as e:
                    return CommandResponse(False, message=f"Piping failed: {e}", error_code="PIPE_ERROR")

            # Normal behavior: Return all data
            return CommandResponse(
                True, 
                message=f"Fetched {len(data)} bars for {ticker}", 
                payload={"ticker": ticker, "data": data}
            )
        except Exception as e:
            import traceback
            sys.stderr.write(traceback.format_exc())
            return CommandResponse(False, message=f"Chart Error: {str(e)}", error_code="CHART_ERROR")

# Registration
registry.register(StatusCommand())
registry.register(TradesCommand())
registry.register(QuoteCommand())
registry.register(ChartCommand())
