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
from .interface import IBrokerAdapter, BrokerUpdate, BarData
from .models import TradeState, TradeMetrics, TradeStatus, TradeTransaction, TradeOrderLog
from py_market_data import ChartManager

class TradeObject:
    @classmethod
    def get_or_create(cls, ticker: str, broker: IBrokerAdapter, storage_dir: str = "./data/trades") -> 'TradeObject':
        """
        [NEW] Factory: Finds latest active trade for ticker OR creates new one.
        Used for 'quote' command to leverage existing state or start a watchlist item.
        """
        ticker = ticker.upper()
        ticker_dir = os.path.join(storage_dir, ticker)
        
        latest_file = None
        latest_time = 0
        
        if os.path.exists(ticker_dir):
            for f in os.listdir(ticker_dir):
                if f.endswith(".json"):
                    fp = os.path.join(ticker_dir, f)
                    mtime = os.path.getmtime(fp)
                    if mtime > latest_time:
                        latest_time = mtime
                        latest_file = f
        
        if latest_file:
            # Load existing
            # We assume filename is ID.json
            trade_id = latest_file.replace(".json", "")
            try:
                obj = cls(ticker=ticker, id=trade_id, storage_dir=storage_dir)
                obj.set_broker(broker)
                return obj
            except Exception as e:
                # Fallback if load fails
                print(f"  [TradeObject] Warning: Could not load existing trade {trade_id}: {e}")
                pass
                
        # Create New (Watchlist/Planned)
        obj = cls(ticker=ticker, storage_dir=storage_dir)
        obj.set_broker(broker)
        # Ensure it is persisted immediately as requested
        obj.save()
        return obj

    @classmethod
    def create_new(cls, ticker: str, broker: Optional[IBrokerAdapter] = None, storage_dir: str = "./data/trades") -> 'TradeObject':
        """
        [NEW] Factory: Explicitly creates a NEW TradeObject (with fresh UUID).
        Does NOT check for existing active trades.
        """
        obj = cls(ticker=ticker, storage_dir=storage_dir)
        if broker:
            obj.set_broker(broker)
        obj.save()
        return obj

    @classmethod
    def from_dict(cls, data: Dict[str, Any], storage_dir: str = "./data/trades") -> 'TradeObject':
        """
        F-TO-021: Reconstructs a TradeObject from a dictionary (TradeState).
        """
        ticker = data.get("ticker", "UNKNOWN")
        # Create obj without ID to avoid constructor loading from file
        obj = cls(ticker=ticker, id=None, storage_dir=storage_dir)
        obj._state = TradeState.from_dict(data)
        # Manually set filepath if id available
        if obj._state.id:
            obj.filepath = os.path.join(obj.storage_dir, f"{obj.ticker}/{obj._state.id}.json")
        return obj

    def __init__(self, ticker: str, id: Optional[str] = None, storage_dir: str = "./data/trades"):
        self.ticker = ticker
        self.storage_dir = os.path.abspath(storage_dir)
        self.id_override = id
        
        # 1. Initialize State
        self._state: Optional[TradeState] = None
        
        # Determine internal ID and Filepath
        if id:
             self.filepath = os.path.join(self.storage_dir, f"{self.ticker}/{id}.json")
             self._load() # Populates self._state
        else:
             new_id = str(uuid.uuid4())
             self.filepath = os.path.join(self.storage_dir, f"{self.ticker}/{new_id}.json")
             self._state = TradeState(id=new_id, ticker=self.ticker, status=TradeStatus.PLANNED)
             # Ensure ticker directory exists
             os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

        # 2. Setup Charting (Internal)
        self.chart_manager = ChartManager(storage_root="./data/market_cache")
        self.broker: Optional[IBrokerAdapter] = None # Broker must be injected via set_broker()
    

    
    def set_broker(self, broker: IBrokerAdapter):
        """Injects the broker adapter dependency."""
        self.broker = broker
        # [NEW] Automatically ensure chart data is present/stale-checked
        try:
            self._ensure_chart()
        except Exception as e:
            # Handle unknown symbols or connection errors gracefully
            # This allows historical reconstruction for dummy/delisted tickers.
            print(f"  [TradeObject] Warning: Could not sync chart for {self.ticker}: {e}")

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

    def _ensure_chart(self, timeframe: str = "1D", lookback: str = "1Y"):
        """
        Internal helper to sync chart data if broker is available.
        """
        if self.broker:
            # ChartManager needs an IMarketDataProvider. self.broker implements this.
            self.chart_manager.provider = self.broker
            self.chart_manager.ensure_data(self.ticker, timeframe, lookback)

    def get_chart(self, timeframe: str = "1D", lookback: str = "1Y") -> List[BarData]:
        """
        F-TO-060: Returns historical chart data.
        Syncs with broker if available.
        """
        try:
            self._ensure_chart(timeframe, lookback)
        except Exception as e:
            # Informative log instead of silence
            print(f"  [TradeObject] Warning: Sync failed during get_chart for {self.ticker}: {e}")
        return self.chart_manager.ensure_data(self.ticker, timeframe, lookback)

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

    def _log_order(self, oid: str, quantity: float, limit: Optional[float], stop: Optional[float], note: str):
        """Helper to append to history."""
        # Determine Type
        otype = "MKT"
        if limit and stop: otype = "BRACKET/STP LMT"
        elif limit: otype = "LMT"
        elif stop: otype = "STP"
        
        log_entry = TradeOrderLog(
            timestamp=datetime.now(),
            order_id=oid,
            action="BUY" if quantity > 0 else "SELL",
            status="SUBMITTED",  # [NEW]
            message=note,        # [NEW]
            quantity=quantity,
            type=otype,
            limit_price=limit,
            stop_price=stop,
            trigger_price=stop, # Simplification for now
            note=note
        )
        self._state.order_history.append(log_entry)

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

        # LOGGING ENTRY
        self._log_order(broker_oid, quantity, limit_price, None, "Initial Entry")

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
            
            # LOGGING STOP
            self._log_order(stop_oid, -quantity, None, stop_loss, "Initial Stop")

            self._state.active_orders[stop_oid] = "STOP"
            self._state.current_stop_price = stop_loss
            # self._state.stop_order_id = stop_oid # Removed as not in original TradeState definition provided

        self.save()
        return broker_oid

    def set_stop_loss(self, new_stop_price: float):
        """
        F-TO-031: Updates the Stop Loss.
        Cancels old stop, places new one.
        Logs the change for R-Factor analysis.
        """
        if not self.broker: raise RuntimeError("Broker missing")
        
        # 1. Find and Cancel old STOP orders
        # Wir suchen in active_orders nach Values "STOP"
        to_cancel = [oid for oid, role in self._state.active_orders.items() if role == "STOP"]
        for oid in to_cancel:
            self.broker.cancel_order(oid)
            del self._state.active_orders[oid]
            
        # 2. Place NEW Stop
        # Menge ist immer Negativ der Net Position
        # Falls Net Quantity 0, nichts tun? Oder Fehler?
        # Annahme: Wir haben eine Position.
        metrics = self.metrics
        qty_to_stop = -metrics.net_quantity
        
        if qty_to_stop == 0:
            raise ValueError("No open position to protect.")

        new_oid = self.broker.place_order(
            order_ref=self.id,
            symbol=self._state.ticker,
            quantity=qty_to_stop,
            stop_price=new_stop_price
        )
        
        # LOGGING THE ADJUSTMENT
        self._log_order(new_oid, qty_to_stop, None, new_stop_price, "Stop Adjustment")
        
        self._state.active_orders[new_oid] = "STOP"
        self._state.current_stop_price = new_stop_price
        self.save()

    def cancel_order(self, order_id: str) -> bool:
        """
        Explicitly cancels a specific active order (e.g. unfilled Entry).
        """
        if not self.broker: raise RuntimeError("Broker missing")

        if order_id not in self._state.active_orders:
            # Maybe it's already gone?
            return False

        # Execute Cancel
        self.broker.cancel_order(order_id)
        
        # Log Logic? 
        # Ideally we get an update 'Cancelled' via refresh(), but eager removal is okay for now?
        # Better to wait for confirmation, but for now we remove it from active set to prevent 'ghosts'.
        # Actually, let's keep it in active set until refresh() confirms it's gone or we trust our command.
        # Strict: Adapter.cancel_order() void.
        
        # We'll just assume it works and remove it from tracking? 
        # No, 'refresh()' handles cleanup.
        return True

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

    def get_quote(self) -> float:
        """
        [NEW] Fetches current price via Broker using established connection.
        Wraps broker.get_current_price().
        """
        if not self.broker:
            raise RuntimeError("Broker missing")
        return self.broker.get_current_price(self.ticker)

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
        # 2. Process New Fills & Log Executions
        existing_ids = {t.id for t in self._state.transactions}
        filled_order_ids = set() # Track orders that got fills in this update
        
        for fill in updates.new_fills:
            # Check if we already have this fill (Idempotency)
            if fill.id not in existing_ids:
                # Calculate Slippage (F-TO-130) handled in logic/models if we pass trigger price
                # For now, just append
                self._state.transactions.append(fill)
                existing_ids.add(fill.id)
                state_changed = True
                
                # LOG EXECUTION
                if fill.order_id:
                    filled_order_ids.add(fill.order_id)
                    
                    # Determine Status (simple heuristic due to lack of order quantity context)
                    fill_status = "FILLED" 
                    fill_msg = f"Filled {fill.quantity} @ {fill.price}"

                    self._state.order_history.append(TradeOrderLog(
                        timestamp=datetime.now(),
                        order_id=fill.order_id,
                        action="BUY" if fill.quantity > 0 else "SELL",
                        status=fill_status,
                        message=fill_msg,
                        quantity=fill.quantity,
                        type="FILL",
                        limit_price=fill.price,
                        stop_price=None
                    ))
                    # Update status of the last log entry for this ID to FILLED?
                    # TradeOrderLog is an append-only event stream. 
                    # We append a NEW event "FILLED" (or "EXECUTION").
                    # Let's verify _log_order usage. It appends. 
                    # We need to set status="FILLED" explicitly.
                    # _log_order defaults status="SUBMITTED". 
                    # We should modify _log_order or manually append.



        # 3. Process Active Orders Cleanup
        # If an order is no longer in updates.active_order_ids, remove it from our tracking
        if updates.active_order_ids is not None:
             current_active_oids = set(updates.active_order_ids)
             tracked_oids = list(self._state.active_orders.keys())
             
             for oid in tracked_oids:
                 if oid not in current_active_oids:
                     # Order is gone (Filled, Cancelled, Expired)
                     role = self._state.active_orders[oid]
                     del self._state.active_orders[oid]
                     state_changed = True
                     
                     # Determine Reason:
                     # If it was in filled_order_ids, it finished filling.
                     # If NOT, it was likely CANCELLED or Rejected.
                     if oid not in filled_order_ids:
                         # Log CANCELLATION
                         self._state.order_history.append(TradeOrderLog(
                            timestamp=datetime.now(),
                            order_id=oid,
                            action="CANCEL", # Action is technically referencing the original order action but here acts as Event Type
                            status="CANCELLED",
                            message="Order removed from active list (Cancelled/Expired)",
                            quantity=0, # No quantity executed
                            type="CANCEL",
                            limit_price=None,
                            stop_price=None
                        ))

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


