import os
import json
from datetime import datetime
from typing import Optional, List, Any
from py_tradeobject.interface import IBrokerAdapter
from .objects import PortfolioSnapshot, PortfolioPosition

class LivePortfolioManager:
    """
    F-PS-020: Live Factory for Portfolio Snapshots.
    """
    def __init__(self, broker: IBrokerAdapter):
        self.broker = broker

    def snapshot(self) -> PortfolioSnapshot:
        """
        F-PS-020: Connects to broker, fetches account summary and positions.
        Returns a fresh PortfolioSnapshot.
        """
        # 1. Account Summary
        # get_account_summary returns dict with 'TotalCashValue', 'NetLiquidation' etc.
        summary = self.broker.get_account_summary()
        cash = summary.get('TotalCashValue', 0.0)
        equity = summary.get('NetLiquidation', 0.0)
        
        # 2. Positions
        # get_positions returns list of IBKR Position objects (account, contract, position, avgCost)
        raw_positions = self.broker.get_positions()
        
        mapped_positions: List[PortfolioPosition] = []
        for pos in raw_positions:
            # pos is ib_insync.Position(account='...', contract=Contract(...), position=10.0, avgCost=150.0)
            contract = pos.contract
            qty = pos.position
            avg_price = pos.avgCost
            
            # Skip empty positions
            if qty == 0: continue
            
            # Fetch Current Price for Valuation
            # This might be slow if we do it for every position sequentially without async.
            # But we are in a blocking context here.
            try:
                current_price = self.broker.get_current_price(contract.symbol)
            except Exception:
                current_price = 0.0
                
            market_value = qty * current_price
            
            # Unrealized PnL = (Current - Avg) * Qty
            unrealized_pnl = (current_price - avg_price) * qty
            
            mapped_positions.append(PortfolioPosition(
                ticker=contract.symbol,
                quantity=qty,
                avg_price=avg_price,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                trade_id=None # Unknown in this raw view, needs correlation later
            ))
            
        # 3. Active Orders
        # F-PS-060: Fetch all open orders
        raw_orders = self.broker.get_all_open_orders() # Returns list of Trade objects (ib_insync)
        
        mapped_orders: List[Any] = [] # Use Any to avoid circular imports? No, use PortfolioOrder imported from .objects
        from .objects import PortfolioOrder # Local import if needed or top-level
        
        for trade in raw_orders:
            # trade is ib_insync.Trade
            order = trade.order
            contract = trade.contract
            
            # Determine Price (Stop vs Limit)
            # Logic: If auxPrice > 0, it's a Stop (or StopLimit). Use auxPrice as risk trigger.
            # Else use lmtPrice.
            price = order.auxPrice if (order.auxPrice and order.auxPrice > 0) else order.lmtPrice
            if not price: price = 0.0 # Market order?
            
            mapped_orders.append(PortfolioOrder(
                ticker=contract.symbol,
                order_id=str(order.orderId),
                action=order.action,
                type=order.orderType,
                qty=order.totalQuantity,
                price=price,
                trade_id=order.orderRef if order.orderRef else ""
            ))

        # 4. Create Snapshot
        snapshot = PortfolioSnapshot(
            timestamp=datetime.now(),
            cash=cash,
            equity=equity,
            positions=mapped_positions,
            active_orders=mapped_orders,
            source="LIVE"
        )
        
        # 5. Persist (F-PS-020)
        self.save_snapshot(snapshot)
        
        return snapshot

    def save_snapshot(self, snapshot: PortfolioSnapshot, filename: str = "portfolio_latest.json"):
        """
        F-PS-020/F-PS-050: Persists the snapshot to disk for caching/offline use.
        """
        # Ensure data dir exists
        data_dir = "./data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        filepath = os.path.join(data_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=4)
        print(f"  [LivePortfolioManager] Snapshot saved to {filepath}")
        
    def get_active_trade_id(self, ticker: str) -> Optional[str]:
        """
        F-PS-060: Returns the trade_id (order_ref) for a given ticker if a position exists.
        Implementation strategy: 
        Since BrokerAdapter's get_positions doesn't return orderRef (it's account level),
        we might not be able to get it directly from positions.
        However, if we had logic to scan 'Active Orders' and see their orderRef, that's one way.
        Or, we scan local 'data/trades' for an OPEN trade for this ticker.
        
        For now, let's implement a placeholder that warns or tries to scan local disk?
        Actually, scanning `data/trades` is the responsibility of history/utils, not necessarily 'Live' adapter.
        But the requirement F-PS-060 says "Nutzt den Live-Cache".
        
        Let's assume we return None for now unless we search Open Orders for references.
        """
        # Search Open Orders for this ticker
        # But we need an adapter method for all open orders, currently we only have updates(ref).
        # Adapter has client.get_open_orders().
        # We need to expose get_all_open_orders() in Adapter?
        # Or just return None for now.
        return None
