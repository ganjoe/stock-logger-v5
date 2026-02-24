# py_cli/handlers_trade.py
import json
from typing import List, Dict, Any
from .models import CLIContext, CommandResponse, CLIMode
from .commands import ICommand, registry
from py_captrader import services
from py_tradeobject.core import TradeObject, TradeStatus

class TradeCommand(ICommand):
    name = "trade"
    description = "PTA Bot Wrapper for all Trade Operations (JSON Payload)."
    syntax = "trade '{\"action\": \"ENTER\", ...}'"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        # 1. Human Guard
        if ctx.mode == CLIMode.HUMAN:
            # We allow it for testing, but warn
            pass

        if not args:
            return CommandResponse(False, message="Missing JSON payload.", error_code="INVALID_ARGS")

        # 2. Parse JSON
        # The args might be split by spaces if quotes were not handled by shell.
        # We try to join them back. 
        # Example: trade '{ "action": "ENTER" }' -> args=['{', '"action":', '"ENTER"', '}']
        raw_json = " ".join(args)
        
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            return CommandResponse(False, message="Invalid JSON format.", error_code="JSON_ERROR")
            
        action = payload.get("action", "").upper()
        if not action:
            return CommandResponse(False, message="Missing 'action' field in payload.", error_code="INVALID_PAYLOAD")

        try:
            # --- DISPATCHER ---
            # CASH action does NOT require broker
            if action == "CASH":
                return self._handle_cash(payload)

            # All other actions require broker connection
            if not services.has_broker():
                return CommandResponse(False, message="No Active Broker Connection.", error_code="NO_CONNECTION")
            
            broker = services.get_broker()

            if action == "ENTER":
                return self._handle_enter(payload, broker)
            elif action == "UPDATE":
                return self._handle_update(payload, broker)
            elif action == "EXIT":
                return self._handle_exit(payload, broker)
            elif action == "CANCEL":
                return self._handle_cancel(payload, broker)
            elif action == "REFRESH":
                return self._handle_refresh(payload, broker)
            else:
                return CommandResponse(False, message=f"Unknown action: {action}", error_code="UNKNOWN_ACTION")
                
        except Exception as e:
            return CommandResponse(False, message=f"Execution Error: {str(e)}", error_code="EXECUTION_ERROR")

    def _handle_enter(self, p: Dict[str, Any], broker) -> CommandResponse:
        ticker = p.get("ticker")
        qty = p.get("quantity")
        limit = p.get("limit_price")
        stop = p.get("stop_loss")
        trade_id = p.get("trade_id") # Optional specific ID
        
        if not ticker or not qty:
            return CommandResponse(False, message="ENTER requires 'ticker' and 'quantity'.", error_code="INVALID_PAYLOAD")
            
        # Create Trade Object
        trade = TradeObject(ticker=ticker, id=trade_id)
        trade.set_broker(broker)
        
        # Execute
        # limit=None → Market Order, limit=float → Limit Order
        broker_oid = trade.enter(quantity=float(qty), limit_price=limit, stop_loss=stop)
        
        return CommandResponse(
            True, 
            message=f"Trade Entered: {ticker}",
            payload={
                "trade_id": trade.id,
                "broker_order_id": broker_oid,
                "status": trade.status.value,
                "ticker": ticker
            }
        )

    def _handle_update(self, p: Dict[str, Any], broker) -> CommandResponse:
        trade_id = p.get("trade_id")
        stop_loss = p.get("stop_loss")
        
        if not trade_id:
             return CommandResponse(False, message="UPDATE requires 'trade_id'.", error_code="INVALID_PAYLOAD")
             
        # Load Trade (implicit via ID)
        # We need to find the ticker for this ID? 
        # TradeObject constructor requires Ticker. 
        # Problem: The Bot gives us ID, do we know the ticker?
        # Ideally the bot gives us the ticker too, OR we look it up.
        # Minimal solution: Bot MUST provide ticker OR we scan (slow).
        # Let's demand ticker for now or use `TradeObject(ticker="UNKNOWN")` and try to load by ID if supported?
        # TradeObject constructor: `TradeObject(ticker, id=...)`. Paths are `./data/trades/{ticker}/{id}.json`.
        # So we NEED the ticker to find the file.
        
        ticker = p.get("ticker")
        if not ticker:
             return CommandResponse(False, message="UPDATE requires 'ticker' (to locate file).", error_code="INVALID_PAYLOAD")

        trade = TradeObject(ticker=ticker, id=trade_id)
        # Verify it loaded (status should not be PLANNED if ID existed)
        if trade.status == TradeStatus.PLANNED:
             # Means we created a new one because file not found
             return CommandResponse(False, message=f"Trade {trade_id} not found for {ticker}.", error_code="NOT_FOUND")
             
        trade.set_broker(broker)
        
        if stop_loss is not None:
            trade.set_stop_loss(float(stop_loss))
            
        return CommandResponse(
            True,
            message=f"Trade Updated: {trade_id}",
            payload={
                "trade_id": trade.id,
                "current_stop_price": trade._state.current_stop_price,
                "status": trade.status.value
            }
        )

    def _handle_exit(self, p: Dict[str, Any], broker) -> CommandResponse:
        trade_id = p.get("trade_id")
        ticker = p.get("ticker")
        
        if not trade_id or not ticker:
             return CommandResponse(False, message="EXIT requires 'trade_id' and 'ticker'.", error_code="INVALID_PAYLOAD")

        trade = TradeObject(ticker=ticker, id=trade_id)
        trade.set_broker(broker)
        
        oid = trade.close()
        
        return CommandResponse(
            True,
            message=f"Trade Closed: {trade_id}",
            payload={
                "trade_id": trade.id,
                "close_order_id": oid,
                "status": trade.status.value
            }
        )

    def _handle_refresh(self, p: Dict[str, Any], broker) -> CommandResponse:
        trade_id = p.get("trade_id")
        ticker = p.get("ticker")
        
        if not trade_id or not ticker:
             return CommandResponse(False, message="REFRESH requires 'trade_id' and 'ticker'.", error_code="INVALID_PAYLOAD")

        trade = TradeObject(ticker=ticker, id=trade_id)
        trade.set_broker(broker)
        
        # Need current price for refresh
        price = trade.get_quote() # F-TO-NEW: Use interface wrapper
        trade.refresh(current_price=price)
        
        return CommandResponse(
            True,
            message=f"Trade Refreshed: {trade_id}",
            payload=trade._state.to_dict()
        )

    def _handle_cancel(self, p: Dict[str, Any], broker) -> CommandResponse:
        trade_id = p.get("trade_id")
        ticker = p.get("ticker")
        order_id = p.get("broker_order_id")

        if not trade_id or not ticker or not order_id:
             return CommandResponse(False, message="CANCEL requires 'trade_id', 'ticker', and 'broker_order_id'.", error_code="INVALID_PAYLOAD")

        trade = TradeObject(ticker=ticker, id=trade_id)
        trade.set_broker(broker)

        success = trade.cancel_order(order_id)
        
        if success:
            return CommandResponse(
                True, 
                message=f"Order {order_id} Cancelled.",
                payload={"trade_id": trade.id, "cancelled_order_id": order_id, "status": "CANCELLED"}
            )
        else:
            return CommandResponse(
                False, 
                message=f"Order {order_id} not active in Trade {trade_id}.",
                error_code="ORDER_NOT_FOUND"
            )

    def _handle_cash(self, p: Dict[str, Any]) -> CommandResponse:
        """
        [F-TO-170] Handles Cash Deposits / Withdrawals.
        No broker connection required.
        Payload: {"action": "CASH", "quantity": 5000, "note": "Monthly Deposit"}
        quantity > 0 = Deposit, quantity < 0 = Withdrawal
        """
        amount = p.get("quantity")
        if amount is None:
            return CommandResponse(False, message="CASH requires 'quantity' (positive=deposit, negative=withdrawal).", error_code="INVALID_PAYLOAD")
        
        amount = float(amount)
        if amount == 0:
            return CommandResponse(False, message="CASH quantity must not be zero.", error_code="INVALID_PAYLOAD")
        
        note = p.get("note", "")
        
        trade = TradeObject.create_cash(amount=amount, note=note)
        action_label = "Deposit" if amount > 0 else "Withdrawal"
        
        return CommandResponse(
            True,
            message=f"💰 {action_label}: {abs(amount):.2f} EUR",
            payload={
                "trade_id": trade.id,
                "trade_type": "CASH",
                "amount": amount,
                "action": action_label,
                "status": trade.status.value
            }
        )

registry.register(TradeCommand())
