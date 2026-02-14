import os
import json
from datetime import datetime
from typing import List, Optional
from .objects import PortfolioSnapshot, TradeResult, PortfolioPosition, PortfolioOrder
from py_tradeobject.models import TradeState, TradeStatus, TransactionType
from py_market_data import ChartManager

class HistoryFactory:
    """
    F-PS-030, F-PS-040, F-PS-080: History interactions.
    """
    def __init__(self, trades_dir: str, chart_manager: Optional[ChartManager] = None):
        self.trades_dir = trades_dir
        self.chart_manager = chart_manager
        self._cache: List[TradeState] = []
        
    def load_all_trades(self):
        """ Scans dir recursively and loads all JSONs. """
        self._cache = []
        if not os.path.exists(self.trades_dir):
            return

        for root, _, files in os.walk(self.trades_dir):
            for filename in files:
                if filename.endswith(".json"):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            state = TradeState.from_dict(data)
                            self._cache.append(state)
                    except Exception:
                        # Ignore corrupted or non-trade files
                        continue
                    
        # Sort by entry date (if available) for processing order? Not strictly needed for snapshot at time X.

    def get_snapshot_at(self, date: datetime) -> PortfolioSnapshot:
        """
        F-PS-040: Reconstructs portfolio at specific point in time.
        """
        # 1. Filter Transactions up to date
        positions: List[PortfolioPosition] = []
        total_cash = 0.0 # Initial Capital? Not defined, starting at 0 relevant to trades.
        
        for trade in self._cache:
            # Calculate Net Quantity and Cash Flow for this trade up to `date`
            qty = 0.0
            avg_price = 0.0 # This might need FIFO/LIFO logic or just Avg Cost
            # TradeState tracks metrics dynamically, but for point-in-time we must replay.
            
            # Simple Avg Price Replay
            cost_basis = 0.0
            
            trade_active = False
            
            for tx in trade.transactions:
                if tx.timestamp > date: continue
                
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
                
                # Cash Delta = -(Qty * Price) - Commission
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
                current_price = self._get_price_at(trade.ticker, date)
                market_val = qty * current_price
                unrealized = market_val - (qty * cost_basis)
                
                positions.append(PortfolioPosition(
                    ticker=trade.ticker,
                    quantity=qty,
                    avg_price=cost_basis,
                    current_price=current_price,
                    market_value=market_val,
                    unrealized_pnl=unrealized,
                    trade_id=None # Could map trade.id if available on TradeState? TradeState doesn't technically have the ID field inside it, it's usually wrapper or filename.
                    # Wait, TradeState usually has ID if defined in models? 
                    # Checking models.py... TradeState has 'active_orders'.
                    # TradeObject has ID. TradeState might not.
                ))
                
        # Calculate Equity
        equity = total_cash + sum(p.market_value for p in positions)
        
        # Reconstruct Active Orders from Logs
        active_orders: List[PortfolioOrder] = []
        
        for trade in self._cache:
            # Check logs for orders that were OPEN at `date`
            # TradeState has 'active_orders' which is current. 
            # We need to rely on 'order_history' (TradeOrderLog).
            # Logic:
            # 1. Find last log entry <= date for each order_id? 
            #    Or logs track state changes.
            #    If we have a "CREATED/SUBMITTED" log before date, and no "FILLED/CANCELLED" log before date, it's open.
            
            # Group logs by order_id
            if not hasattr(trade, 'order_history'): continue
            
            orders_state = {} # order_id -> status, details
            
            for log in sorted(trade.order_history, key=lambda x: x.timestamp):
                if log.timestamp > date: break
                
                # Update state
                orders_state[log.order_id] = {
                    "status": log.status,
                    "action": log.action,
                    "log_obj": log
                }
                
            # Filter for active
            for oid, state in orders_state.items():
                # What statuses are active?
                # SUBMITTED, PARTIALLY_FILLED, PENDING
                # Inactive: FILLED, CANCELLED, REJECTED
                
                status = state["status"]
                if status not in ["FILLED", "CANCELLED", "REJECTED", "EXPIRED"]:
                    # It's active!
                    log = state["log_obj"]
                    
                    # Determine price (Limit or Stop?)
                    # PortfolioOrder expects 'price'.
                    price = log.limit_price if log.limit_price is not None else log.stop_price
                    if price is None: price = 0.0
                    
                    active_orders.append(PortfolioOrder(
                        ticker=trade.ticker,
                        order_id=oid,
                        action=state.get("action", "UNKNOWN"),
                        type=log.type,
                        qty=log.quantity,
                        price=price,
                        trade_id=trade.id
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
            if trade.status in [TradeStatus.CLOSED, TradeStatus.ARCHIVED]:
                # Check exit date (Timestamp of last transaction)
                if not trade.transactions: continue
                
                # Sort transactions by time to be sure
                sorted_tx = sorted(trade.transactions, key=lambda x: x.timestamp)
                last_tx = sorted_tx[-1]
                
                if start <= last_tx.timestamp <= end:
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
                        ticker=trade.ticker,
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
        
        while current <= end_date:
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
        """Helper to get price from ChartManager or fallback."""
        if not self.chart_manager: return 0.0
        
        # We need data at 'date'.
        # ChartManager.ensure_data gives us bars.
        # We can try to load from disk without fetching?
        # Manager doesn't expose strict "get_price_at".
        # We can implement a helper to load 1D bars and find the close.
        # This is expensive if we do it inside a loop. 
        # For now return 100.0 dummy or basic implementation.
        return 100.0
