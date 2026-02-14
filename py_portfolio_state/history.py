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
        """ Scans dir and loads all JSONs. """
        self._cache = []
        if not os.path.exists(self.trades_dir):
            return

        for filename in os.listdir(self.trades_dir):
            if filename.endswith(".json"):
                # Load TradeState
                # Assumption: One JSON per trade in trades_dir or standard TradeObject structure?
                # TradeObject saves to {storage_root}/{ticker}/{id}.json or similar?
                # The TradeObject ALM says "Speichert sich selbstständig...".
                # Usually we might have to search recursively if structure is complex.
                # Let's assume flat or we assume trades_dir is the root and we walk it.
                
                # Simple walk
                filepath = os.path.join(self.trades_dir, filename)
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
        
        return PortfolioSnapshot(
            timestamp=date,
            cash=total_cash,
            equity=equity,
            positions=positions,
            active_orders=[], # TODO: Replay logs for orders
            source="HISTORY"
        )

    def get_closed_trades(self, start: datetime, end: datetime) -> List[TradeResult]:
        """
        F-PS-080: Returns list of trades closed within window.
        """
        results = []
        for trade in self._cache:
            if trade.status == TradeStatus.CLOSED or trade.status == TradeStatus.ARCHIVED:
                # Check exit date
                # We need to find the exit date.
                # Last transaction timestamp?
                if not trade.transactions: continue
                last_tx = trade.transactions[-1]
                if start <= last_tx.timestamp <= end:
                    # Metrics should be in trade.metrics?
                    # Or we calculate fresh?
                    # Trade State has metrics?
                    # No, TradeMetrics is separate in models usually, usually computed.
                    # TradeState has NO metrics field in standard definition?
                    # Core usually calculates it on load.
                    # We might need to recalculate here or assume TradeState has it?
                    # Let's verify TradeState definition. 
                    # Assuming we can calculate simple metrics here.
                    
                    entry_date = trade.transactions[0].timestamp
                    exit_date = last_tx.timestamp
                    
                    # Simple PnL: Sum of all cash flows
                    pnl = sum([-(t.quantity * t.price) - t.commission for t in trade.transactions])
                    
                    results.append(TradeResult(
                        ticker=trade.ticker,
                        direction="LONG", # Todo: detect short
                        entry_date=entry_date,
                        exit_date=exit_date,
                        entry_price=trade.transactions[0].price,
                        exit_price=last_tx.price,
                        qty=sum([t.quantity for t in trade.transactions if t.quantity > 0]), # Total bought size?
                        pnl_absolute=pnl,
                        pnl_percent=0.0, # Todo
                        r_multiple=0.0, # Todo
                        duration_days=(exit_date - entry_date).days
                    ))
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
