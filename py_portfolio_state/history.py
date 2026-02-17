import os
import json
from datetime import datetime
from typing import List, Optional
from .objects import PortfolioSnapshot, TradeResult, PortfolioPosition, PortfolioOrder
from py_tradeobject.models import TradeState, TradeStatus, TransactionType
from py_tradeobject.core import TradeObject
from py_tradeobject.interface import IBrokerAdapter

class HistoryFactory:
    """
    F-PS-030, F-PS-040, F-PS-080: History interactions.
    """
    def __init__(self, trades_dir: str, provider: Optional[IBrokerAdapter] = None):
        self.trades_dir = trades_dir
        self.provider = provider
        self._cache: List[TradeObject] = []
        
    def load_all_trades(self):
        """
        F-PS-050: Recursively loads all trade JSONs from trades_dir.
        """
        self._cache = []
        if not os.path.exists(self.trades_dir):
            return

        for root, _, files in os.walk(self.trades_dir):
            for file in files:
                if file.endswith(".json"):
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, "r") as f:
                            data = json.load(f)
                            trade_obj = TradeObject.from_dict(data)
                            
                            # Inject Provider if available
                            if self.provider:
                                trade_obj.set_broker(self.provider)
                                
                            self._cache.append(trade_obj)
                    except Exception as e:
                        pass

    def get_snapshot_at(self, date: datetime) -> PortfolioSnapshot:
        """
        F-PS-070: Reconstructs portfolio state at a specific point in time.
        """
        total_cash = 0.0 # TODO: Load from cash log
        positions: List[PortfolioPosition] = []
        
        for trade in self._cache:
            # We are now iterating TradeObjects. Need to access _state for data.
            state = trade._state # Accessing protected member for analysis
            if not state: continue

            # Calculate Net Quantity and Cash Flow for this trade up to `date`
            qty = 0.0
            avg_price = 0.0 # This might need FIFO/LIFO logic or just Avg Cost
            # TradeState tracks metrics dynamically, but for point-in-time we must replay.
            
            # Simple Avg Price Replay
            cost_basis = 0.0
            
            trade_active = False
            
            for tx in state.transactions:
                # Ensure both are naive for comparison
                tx_ts = tx.timestamp.replace(tzinfo=None) if tx.timestamp.tzinfo else tx.timestamp
                target_dt = date.replace(tzinfo=None) if date.tzinfo else date
                
                if tx_ts > target_dt: continue
                
                # Apply TX
                # Cash Flow
                # Buying: - (Price * Qty) - Comm
                # Selling: + (Price * Qty) - Comm
                
                # TransactionType: ENTRY, EXIT, ADJUSTMENT
                # Qty is signed in TradeTransaction?
                # models.py says: "quantity: float # Signed Value: + for Long-Buys..."
                # Wait, usually for Long: Buy=+Qty, Sell=-Qty.
                # Transaction Cost = Price * Qty.
                # If Buy 10 @ 100 -> Cost 1000. Cash -1000.
                
                # Cash Delta = -(tx.quantity * tx.price) - tx.commission
                cash_delta = -(tx.quantity * tx.price) - tx.commission
                total_cash += cash_delta
                
                # Position Update
                qty += tx.quantity
                
                # Update Cost Basis (Simple Weighted Avg for Longs)
                # If we are adding to position (Long Buy)
                if tx.quantity > 0:
                     total_cost = (cost_basis * (qty - tx.quantity)) + (tx.quantity * tx.price)
                     cost_basis = total_cost / qty if qty != 0 else 0
                     
                trade_active = (qty != 0)
            
            # If active position exists
            if trade_active and qty != 0:
                # Valuation
                current_price = self._get_price_at(state.ticker, date)
                market_val = qty * current_price
                unrealized = market_val - (qty * cost_basis)
                
                positions.append(PortfolioPosition(
                    ticker=state.ticker,
                    quantity=qty,
                    avg_price=cost_basis,
                    current_price=current_price,
                    market_value=market_val,
                    unrealized_pnl=unrealized,
                    trade_id=state.id
                ))
                
        # Calculate Equity
        equity = total_cash + sum(p.market_value for p in positions)
        
        # Reconstruct Active Orders from Logs
        active_orders: List[PortfolioOrder] = []
        
        for trade in self._cache:
            # Check logs for orders that were OPEN at `date`
            state = trade._state
            if not getattr(state, 'order_history', None): 
                continue
            
            orders_state = {} # order_id -> status, details
            
            for log in sorted(state.order_history, key=lambda x: x.timestamp):
                # Ensure both are naive for comparison
                log_ts = log.timestamp.replace(tzinfo=None) if log.timestamp.tzinfo else log.timestamp
                target_dt = date.replace(tzinfo=None) if date.tzinfo else date
                
                if log_ts > target_dt: 
                    break
                
                # Update state
                orders_state[log.order_id] = {
                    "status": log.status,
                    "action": log.action,
                    "log_obj": log
                }

            # Filter for active
            for oid, state_dict in orders_state.items():
                # What statuses are active?
                # SUBMITTED, PARTIALLY_FILLED, PENDING
                # Inactive: FILLED, CANCELLED, REJECTED
                
                status = state_dict["status"]
                if status not in ["FILLED", "CANCELLED", "REJECTED", "EXPIRED"]:
                    # It's active!
                    log = state_dict["log_obj"]
                    
                    # Determine price (Limit or Stop?)
                    # PortfolioOrder expects 'price'.
                    price = log.limit_price if log.limit_price is not None else log.stop_price
                    if price is None: price = 0.0
                    
                    active_orders.append(PortfolioOrder(
                        ticker=state.ticker,
                        order_id=oid,
                        action=state_dict.get("action", "UNKNOWN"),
                        type=log.type,
                        qty=log.quantity,
                        price=price,
                        trade_id=state.id
                    ))

        return PortfolioSnapshot(
            timestamp=date,
            cash=total_cash,
            equity=equity,
            positions=positions,
            active_orders=active_orders,
            source="HISTORY"
        )

    def get_closed_trades(self, start: datetime, end: datetime) -> List[TradeResult]:
        """
        F-PS-080: Returns list of trades closed within window.
        """
        results = []
        for trade in self._cache:
            state = trade._state
            if not state: continue

            if state.status in [TradeStatus.CLOSED, TradeStatus.ARCHIVED]:
                # Check exit date (Timestamp of last transaction)
                if not state.transactions: continue
                
                # Sort transactions by time to be sure
                sorted_tx = sorted(state.transactions, key=lambda x: x.timestamp)
                last_tx = sorted_tx[-1]
                
                # Ensure all are naive for comparison
                last_tx_ts = last_tx.timestamp.replace(tzinfo=None) if last_tx.timestamp.tzinfo else last_tx.timestamp
                start_dt = start.replace(tzinfo=None) if start.tzinfo else start
                end_dt = end.replace(tzinfo=None) if end.tzinfo else end
                
                if start_dt <= last_tx_ts <= end_dt:
                    entry_tx = sorted_tx[0]
                    entry_date = entry_tx.timestamp
                    exit_date = last_tx.timestamp
                    
                    # Calculate PnL: Sum of all cash flows (Prices are positive, Qty signed?)
                    # TradeTransaction models usually store:
                    # type=ENTRY, quantity=10 (Long), price=100
                    # type=EXIT, quantity=-10 (Sell), price=110
                    # Cash Flow = -(Qty * Price) - Commission
                    
                    pnl = 0.0
                    total_bought_qty = 0.0
                    
                    for tx in sorted_tx:
                        cash_flow = -(tx.quantity * tx.price) - tx.commission
                        pnl += cash_flow
                        if tx.quantity > 0:
                            total_bought_qty += tx.quantity

                    # Direction
                    direction = "LONG" if total_bought_qty > 0 else "SHORT" # Simplified
                    
                    results.append(TradeResult(
                        ticker=state.ticker,
                        direction=direction,
                        entry_date=entry_date,
                        exit_date=exit_date,
                        entry_price=entry_tx.price,
                        exit_price=last_tx.price,
                        qty=total_bought_qty,
                        pnl_absolute=pnl,
                        pnl_percent=0.0, # Todo: Calculate return on risk/capital
                        r_multiple=0.0, # Todo: Requires initial risk
                        duration_days=(exit_date - entry_date).days
                    ))
        return results

    def get_daily_snapshots(self, start_date: datetime, end_date: datetime) -> List[PortfolioSnapshot]:
        """
        F-PS-070: Generates a list of PortfolioSnapshots, one for each day in range (EOD).
        """
        results = []
        current = start_date
        
        while True:
            # Ensure both are naive for comparison
            curr_ts = current.replace(tzinfo=None) if current.tzinfo else current
            end_ts = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
            
            if curr_ts > end_ts:
                break
            # Set to End of Day (23:59:59)
            eod_timestamp = current.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Replay
            snapshot = self.get_snapshot_at(eod_timestamp)
            results.append(snapshot)
            
            # Next day
            # If current is datetime, use timedelta
            import datetime as dt
            current += dt.timedelta(days=1)
            
        return results

    def _get_price_at(self, ticker: str, date: datetime) -> float:
        """Helper to get price from TradeObject's ChartManager or fallback."""
        # Find ANY trade object for this ticker 
        # (Charts are per ticker, so any instance logic is fine, or create temp one)
        
        trade = next((t for t in self._cache if t.ticker == ticker), None)
        if not trade:
             # If we don't have a trade in cache, we can't easily access chart manager logic encapsulated in TradeObject
             # unless we instantiate a dummy one.
             # fallback
             return 0.0
             
        try:
             # This uses TradeObject's internal mechanism (including auto-fetch via provider if injected)
             bars = trade.get_chart("1D", "1Y")
             
             if not bars: return 0.0
             
             # 3. Find closest bar <= date
             # Binary search or simple iteration (bars are sorted)
             closest_price = 0.0
             found = False
             
             for bar in reversed(bars):
                 if bar.timestamp.date() <= date.date():
                     closest_price = bar.close
                     found = True
                     break
             
             if not found:
                 # Date might be before first bar? Return first bar open?
                 closest_price = bars[0].open
                 
             return closest_price
             
        except Exception:
            return 0.0
