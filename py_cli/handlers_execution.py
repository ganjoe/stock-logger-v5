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
            return CommandResponse(False, "Usage: close <trade_id> [--force]", error_code="INVALID_ARGS")

        trade_id = args[0]
        # Check Force Flag
        force = "--force" in args or "--confirm" in args
        
        # SAFETY CHECK F-SEC-020
        if ctx.mode == CLIMode.HUMAN:
            # Interactive Confirmation (Pseudo-code, CLI Controller usually handles input loop)
            # But since execute is atomic, we return a "Please Confirm" message if not forced?
            # Actually, standard CLI practice: if not forced, prompt.
            # However, prompt requires input()... which blocks. 
            # In this architecture, maybe we expect the user to type 'close <id> --confirm'?
            # Let's enforce explicit --confirm for now, or just return a warning.
            if not force:
                 return CommandResponse(False, message=f"⚠️  SAFETY: To close {trade_id}, you must append --confirm or --force.", error_code="CONFIRM_REQUIRED")
        
        elif ctx.mode == CLIMode.BOT:
            if not (force or ctx.confirm_all):
                return CommandResponse(False, message="SAFETY: Bot must use --confirm or context.confirm_all=True", error_code="SAFETY_LOCK")

        # Mock Logic
        return CommandResponse(True, message=f"Trade {trade_id} closed successfully.", payload={"trade_id": trade_id, "status": "CLOSED"})

class OrderCommand(ICommand):
    name = "order"
    description = "Places a new order."
    syntax = "order <side> <ticker> <qty>"
    
    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        # Simplistic implementation
        if len(args) < 3:
             return CommandResponse(False, message="Usage: order <buy/sell> <ticker> <qty>", error_code="INVALID_ARGS")
             
        side, ticker, qty = args[0], args[1], args[2]
        
        # Bot Safety
        if ctx.mode == CLIMode.BOT and not ctx.confirm_all and "--confirm" not in args:
             return CommandResponse(False, message="SAFETY: Order requires confirmation.", error_code="SAFETY_LOCK")

        return CommandResponse(True, message=f"Order Placed: {side} {qty} {ticker}", payload={"order_id": "mock_oid_123"})

# Registration
registry.register(CloseCommand())
registry.register(OrderCommand(), aliases=["orders"])
