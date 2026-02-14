"""
py_tradeobject/core.py
Service Orchestration (The "TradeObject"). STATE & IO.
"""
import os
import json
import uuid
import time
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any

from .models import TradeState, TradeMetrics, TradeStatus, TradeTransaction
from .logic import TradeCalculator
from .interface import IBrokerAdapter, BrokerUpdate

class TradeObject:
    def __init__(self, ticker: str, id: Optional[str] = None, storage_dir: str = "./data/trades"):
        self.ticker = ticker
        self.storage_dir = os.path.abspath(storage_dir)
        self.ticker_dir = os.path.join(self.storage_dir, ticker)
        
        # Ensure directories exist
        os.makedirs(self.ticker_dir, exist_ok=True)
        
        # State loaded flag
        self._state: Optional[TradeState] = None
        
        if id:
            # Try load existing
            potential_path = os.path.join(self.ticker_dir, f"{id}.json")
            if os.path.exists(potential_path):
                self.filepath = potential_path
                self._load()
            else:
                # Specified ID but file missing -> New Trade with this ID
                self.filepath = potential_path
                self._state = TradeState(id=id, ticker=ticker, status=TradeStatus.PLANNED)
                self.save()
        else:
            # New Trade -> Generate ID
            new_id = str(uuid.uuid4())
            self.filepath = os.path.join(self.ticker_dir, f"{new_id}.json")
            self._state = TradeState(id=new_id, ticker=ticker, status=TradeStatus.PLANNED)
            self.save()
            
        self.broker: Optional[IBrokerAdapter] = None # Broker must be injected via set_broker()
    
    def set_broker(self, broker: IBrokerAdapter):
        """Injects the broker adapter dependency."""
        self.broker = broker

    @property
    def id(self) -> str:
        return self._state.id

    @property
    def status(self) -> TradeStatus:
        return self._state.status

    @property
    def metrics(self) -> TradeMetrics:
        """Calculates and returns current metrics based on state."""
        # Intrinsic metrics requires a price for Unrealized PnL.
        # Ideally this would accept current_price or fetch it.
        # Fallback: Use last execution price.
        current_price = 0.0
        if self._state.transactions:
             current_price = self._state.transactions[-1].price
        
        # Initial Risk is stored in state
        initial_risk = 0.0
        if self._state.initial_stop_price and self._state.transactions:
            # Calculate Risk based on First Entry
            # Risk = |EntryPrice - StopPrice| * Qty
            first_tx = self._state.transactions[0]
            initial_risk = abs(first_tx.price - self._state.initial_stop_price) * abs(first_tx.quantity)

        return TradeCalculator.calculate_metrics(self._state.transactions, current_price, initial_risk)

    def _load(self):
        """Loads state from JSON."""
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
                self._state = TradeState.from_dict(data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise RuntimeError(f"Failed to load TradeObject {self.filepath}: {e}")

    def save(self):
        """
        Persists state to JSON with Atomic Write (Cross-Platform).
        [F-TO-040, F-TO-041]
        """
        if not self._state: return

        # 1. Serialize
        data = self._state.to_dict()
        
        # 2. Write to Temp File
        tmp_path = self.filepath + ".tmp"
        with open(tmp_path, 'w') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno()) # Ensure write to disk

        # 3. Atomic Move (Retry Loop for Windows)
        max_retries = 5
        for i in range(max_retries):
            try:
                os.replace(tmp_path, self.filepath)
                break
            except OSError:
                # On Windows, os.replace fails if dest exists and is locked.
                if i < max_retries - 1:
                    time.sleep(0.05 * (i + 1)) # Conditional backoff
                else:
                    # Final attempt: Remove dest then Rename (Python < 3.3 atomicity workaround behavior)
                    try:
                        if os.path.exists(self.filepath):
                            os.remove(self.filepath)
                        os.rename(tmp_path, self.filepath)
                    except Exception as e:
                        print(f"CRITICAL: Failed to save TradeObject {self.id}: {e}")
                        # Leave tmp file for recovery

    # --- API COMMANDS (F-TO-030 bis F-TO-072) ---

    def enter(self, quantity: float, limit_price: Optional[float] = None, stop_loss: Optional[float] = None) -> str:
        """
        F-TO-030: Places entry order via broker.
        Sets status to OPENING (Async).
        """
        if not self.broker:
            raise RuntimeError("Broker not injected. Call set_broker() first.")

        if self.status not in [TradeStatus.PLANNED, TradeStatus.CLOSED]: # Allow re-entry if closed? Discuss. For now strict.
             # Actually, re-entry might be valid if we want to "add" to a position. 
             # But usually 'enter' implies starting. 'scale_in' would be another method.
             # Let's keep it restricted to PLANNED for now to follow lifecycle.
             if self.status != TradeStatus.PLANNED:
                raise ValueError(f"Cannot enter trade in status {self.status}")

        # 1. Place Order (Async)
        # We pass self.id as order_ref for F-TO-140
        broker_oid = self.broker.place_order(
            order_ref=self.id,
            symbol=self._state.ticker,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=None # Stop loss is usually a separate order or bracket
        )

        # 2. Update State
        self._state.status = TradeStatus.OPENING
        self._state.active_orders[broker_oid] = "ENTRY"
        
        # 3. Handle Initial Stop Loss (Optional separate order)
        if stop_loss:
            self._state.initial_stop_price = stop_loss
            # In a real bracket system, this might be linked. 
            # Here we place a separate stop order.
            stop_oid = self.broker.place_order(
                order_ref=self.id,
                symbol=self._state.ticker,
                quantity=-quantity, # Sell to stop (Simplified logic, check broker adapter implementation for smarts)
                stop_price=stop_loss
            )
            self._state.active_orders[stop_oid] = "STOP"
            self._state.current_stop_price = stop_loss
            self._state.stop_order_id = stop_oid

        self.save()
        return broker_oid

    def close(self) -> str:
        """
        F-TO-033: Closes remaining position at market.
        Cancels open orders.
        """
        if not self.broker: raise RuntimeError("Broker missing")

        metrics = self.metrics
        if metrics.net_quantity == 0:
            self._state.status = TradeStatus.CLOSED
            self.save()
            return "ALREADY_FLAT"

        # 1. Cancel all active orders (Stops/Limits)
        for oid in list(self._state.active_orders.keys()):
            self.broker.cancel_order(oid)
        self._state.active_orders.clear()

        # 2. Place Closing Order
        close_oid = self.broker.place_order(
            order_ref=self.id,
            symbol=self._state.ticker,
            quantity=-metrics.net_quantity, # Flatten
            limit_price=None # Market
        )
        
        self._state.status = TradeStatus.CLOSING
        self._state.active_orders[close_oid] = "EXIT"
        self.save()
        return close_oid

    def refresh(self, current_price: float):
        """
        F-TO-050: Syncs with broker and updates metrics.
        CRITICAL: Requires current_price to calculate accurate PnL.
        """
        if not self.broker: raise RuntimeError("Broker missing")

        # 1. Get Updates from Broker (Fills & Status)
        # Returns dataclass BrokerUpdate(new_fills, active_ids, cancelled_ids)
        # Using the ID as Reference
        updates = self.broker.get_updates(order_ref=self.id)

        state_changed = False

        # 2. Process New Fills
        existing_ids = {t.id for t in self._state.transactions}
        for fill in updates.new_fills:
            # Check if we already have this fill (Idempotency)
            if fill.id not in existing_ids:
                # Calculate Slippage (F-TO-130) handled in logic/models if we pass trigger price
                # For now, just append
                self._state.transactions.append(fill)
                existing_ids.add(fill.id)
                state_changed = True

        # 3. Process Active Orders Cleanup
        # If an order is no longer in updates.active_order_ids, remove it from our tracking
        if updates.active_order_ids is not None:
             current_active_oids = set(updates.active_order_ids)
             tracked_oids = list(self._state.active_orders.keys())
             
             for oid in tracked_oids:
                 if oid not in current_active_oids:
                     # Order is gone (Filled, Cancelled, Expired)
                     # We assume Fills are handled above via new_fills.
                     # So we just remove it from tracking map.
                     del self._state.active_orders[oid]
                     state_changed = True

        # 4. Update Status Logic (F-TO-120)
        # Re-calculate net quantity to check if we are OPEN or CLOSED
        # Pass current_price to calc metrics for status decision? Not strictly needed for Qty.
        metrics = TradeCalculator.calculate_metrics(self._state.transactions, current_price)
        
        # Transition Logic
        if self._state.status == TradeStatus.OPENING and metrics.net_quantity != 0:
            self._state.status = TradeStatus.OPEN
            state_changed = True
        
        elif self._state.status in [TradeStatus.OPEN, TradeStatus.CLOSING] and metrics.net_quantity == 0:
            # Only set CLOSED if we have no active orders left (Clean exit)
            if not self._state.active_orders:
                self._state.status = TradeStatus.CLOSED
                state_changed = True

        if state_changed:
            self.save()

    def get_event_stream(self) -> List[Dict[str, Any]]:
        """
        F-TO-072: Returns standardized event stream for Portfolio Timeline.
        """
        events = []
        for t in self._state.transactions:
            # Cash Flow: Negative for Buy, Positive for Sell
            # Logic: (Qty * Price * -1) - Comm
            # Buy 10 @ 100 = -1000. Sell 10 @ 110 = +1100. Net +100.
            cash_flow = (t.quantity * t.price * -1) - t.commission
            
            events.append({
                "timestamp": t.timestamp.isoformat(),
                "trade_id": self.id,
                "ticker": self._state.ticker,
                "type": t.type.value if hasattr(t.type, 'value') else str(t.type),
                "quantity_change": t.quantity,
                "cash_flow": cash_flow,
                "price": t.price
            })
        
        # Sort by timestamp
        return sorted(events, key=lambda x: x["timestamp"])
