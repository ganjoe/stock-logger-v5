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

    def save_snapshot(self, snapshot: PortfolioSnapshot):
        """Persists the latest snapshot to disk."""
        path = "./data/portfolio_latest.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

    def snapshot(self, ticker: Optional[str] = None) -> PortfolioSnapshot:
        """
        F-PS-020: Connects to broker, fetches account summary and positions.
        Optional ticker filter for token efficiency.
        """
        # 1. Account Summary
        summary = self.broker.get_account_summary()
        cash = summary.get('TotalCashValue', 0.0)
        equity = summary.get('NetLiquidation', 0.0)
        
        # 2. Positions
        raw_positions = self.broker.get_positions()
        mapped_positions: List[PortfolioPosition] = []
        for pos in raw_positions:
            contract = pos.contract
            
            # Filter by Ticker if requested
            if ticker and contract.symbol != ticker:
                continue

            qty = pos.position
            avg_price = pos.avgCost
            if qty == 0: continue
            
            try:
                current_price = self.broker.get_current_price(contract.symbol)
            except Exception:
                current_price = 0.0
                
            mapped_positions.append(PortfolioPosition(
                ticker=contract.symbol,
                quantity=qty,
                avg_price=avg_price,
                current_price=current_price,
                market_value=qty * current_price,
                unrealized_pnl=(current_price - avg_price) * qty
            ))
            
        # 3. Active Orders
        raw_orders = self.broker.get_all_open_orders() 
        from .objects import PortfolioOrder
        
        mapped_orders: List[PortfolioOrder] = []
        for trade in raw_orders:
            order = trade.order
            contract = trade.contract

            # Filter by Ticker if requested
            if ticker and contract.symbol != ticker:
                continue
            
            price = order.auxPrice if (order.auxPrice and order.auxPrice > 0) else order.lmtPrice
            mapped_orders.append(PortfolioOrder(
                ticker=contract.symbol,
                order_id=str(order.orderId),
                action=order.action,
                type=order.orderType,
                qty=order.totalQuantity,
                price=price or 0.0,
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
