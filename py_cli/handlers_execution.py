"""
py_cli/handlers_execution.py
Implementation of Execution Commands (close, order) with SAFETY PROTOCOLS.
"""
from typing import List
from .models import CLIContext, CommandResponse, CLIMode
from .commands import ICommand, registry

class CloseCommand(ICommand):
    name = "close"
    description = "Closes a trade by ID. REQUIRES CONFIRMATION."
    syntax = "close <trade_id> [--force]"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        if not args:
             return CommandResponse(success=False, message="Usage: close <trade_id> [--force]", error_code="INVALID_ARG")

        trade_id = args[0]
        # Check Force Flag
        force = "--force" in args or "--confirm" in args
        
        # SAFETY CHECK F-SEC-020
        if ctx.mode == CLIMode.HUMAN and not force:
            return CommandResponse(success=False, message=f"⚠️  SAFETY: To close {trade_id}, you must append --confirm or --force.", error_code="CONFIRM_REQUIRED")
        
        if ctx.mode == CLIMode.BOT and not (force or ctx.confirm_all):
            return CommandResponse(success=False, message="SAFETY: Bot must use --confirm or context.confirm_all=True", error_code="SAFETY_LOCK")

        if not services.has_broker():
            return CommandResponse(success=False, message="No Active Broker Connection.", error_code="NO_CONNECTION")

        try:
            broker = services.get_broker()
            storage_dir = ctx.trades_dir or "/home/daniel/stock-data-node/data/parquet"
            
            # 1. Find Ticker for this Trade ID (Search in storage_dir)
            import glob
            import os
            pattern = os.path.join(storage_dir, "*", f"{trade_id}.json")
            matches = glob.glob(pattern)
            
            if not matches:
                return CommandResponse(success=False, message=f"Trade {trade_id} not found in {storage_dir}.", error_code="NOT_FOUND")
            
            # Ticker is the parent directory name
            ticker = os.path.basename(os.path.dirname(matches[0]))
            
            # 2. Load TradeObject
            from py_tradeobject.core import TradeObject
            trade = TradeObject(ticker=ticker, id=trade_id, storage_dir=storage_dir)
            trade.set_broker(broker)
            
            # 3. Execute Close
            print(f"  [CLI] Executing Live Close for {ticker} (ID: {trade_id})...")
            result = trade.close()
            
            return CommandResponse(
                success=True, 
                message=f"Close order placed for {ticker} (ID: {trade_id}). Result: {result}", 
                payload={"trade_id": trade_id, "ticker": ticker, "status": "CLOSING", "broker_oid": result}
            )
            
        except Exception as e:
            return CommandResponse(success=False, message=f"Close Error: {str(e)}", error_code="EXECUTION_ERROR")

# Registration
registry.register(CloseCommand())
