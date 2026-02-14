"""
py_tradeobject/logic.py
Business Rules & Calculations. PURE FUNCTIONS.
"""
from typing import List, Optional
from datetime import datetime
from .models import TradeTransaction, TradeMetrics

class TradeCalculator:
    """Pure logic class for deriving metrics and status."""
    
    @staticmethod
    def calculate_metrics(transactions: List[TradeTransaction], current_price: float, initial_risk: float = 0.0) -> TradeMetrics:
        """
        Derives all metrics using Weighted Average Price logic.
        
        Algorithm:
        1. Sort transactions by timestamp.
        2. Iterate through transactions to rebuild position state.
           - Same Sign (Building): Update Avg Price.
           - Different Sign (Reducing): Calc Realized PnL, Keep Avg Price.
           - Flip (Long -> Short): Close old PnL, Start new Avg Price.
        """
        # Sortiere sicherheitshalber nach Zeit (auch wenn das TradeObjects selbst machen sollte)
        sorted_tx = sorted(transactions, key=lambda t: t.timestamp)
        
        net_qty = 0.0
        avg_price = 0.0
        realized_pnl = 0.0
        total_commissions = 0.0
        first_entry_time = None
        last_tx_time = None
        
        for t in sorted_tx:
            # 0. Commission always accumulates
            total_commissions += t.commission
            
            if not first_entry_time:
                first_entry_time = t.timestamp
            last_tx_time = t.timestamp

            # 1. Determine Position Impact
            # t.quantity is signed (+ for Long Buy, - for Long Sell/Short Sell)
            
            if net_qty == 0:
                # OPEN NEW POSITION (or Flip to new side)
                net_qty = t.quantity
                avg_price = t.price
            
            elif (net_qty > 0 and t.quantity > 0) or (net_qty < 0 and t.quantity < 0):
                # ASCENDING / BUILDING (Same Direction)
                # Weighted Average Price: (OldVal + NewVal) / NewQty
                # Note: Using abs() allows valid math for both Long and Short averaging
                total_value = (abs(net_qty) * avg_price) + (abs(t.quantity) * t.price)
                net_qty += t.quantity
                avg_price = total_value / abs(net_qty)
                
            else:
                # REDUCING / CLOSING / FLIPPING (Opposite Direction)
                
                # Case A: Partial/Full Closing
                if abs(t.quantity) <= abs(net_qty):
                    # Realize PnL on closed portion
                    # For Long (net>0, tx<0):  PnL = (SellPrice - AvgPrice) * QtySold
                    # For Short (net<0, tx>0): PnL = (AvgPrice - BuyPrice) * QtyBought (inverted logic)
                    
                    qty_closed = abs(t.quantity)
                    
                    if net_qty > 0: # Long Closing
                        trade_pnl = (t.price - avg_price) * qty_closed
                    else: # Short Closing
                        trade_pnl = (avg_price - t.price) * qty_closed
                    
                    realized_pnl += trade_pnl
                    net_qty += t.quantity # Reduces magnitude
                    
                    # If position closed exactly to 0, reset avg_price just to be clean
                    if round(net_qty, 8) == 0:
                        net_qty = 0.0
                        avg_price = 0.0
                        
                # Case B: FLIP (Close full + Open new opposite)
                # Example: Long 10 -> Sell 20 -> Short 10
                else:
                    # 1. Close current fully
                    qty_closed = abs(net_qty)
                    if net_qty > 0: # Long Closing
                        trade_pnl = (t.price - avg_price) * qty_closed
                    else: # Short Closing
                        trade_pnl = (avg_price - t.price) * qty_closed
                    
                    realized_pnl += trade_pnl
                    
                    # 2. Open remainder as new position
                    # Remaining is simply the sum, as signs are opposite
                    # e.g. +10 (Long) + -20 (Sell) = -10 (New Short)
                    remaining_qty = net_qty + t.quantity
                    net_qty = remaining_qty
                    avg_price = t.price # New basis is execution price
        
        # Final Calculations
        unrealized_pnl = 0.0
        if net_qty != 0:
            if net_qty > 0:
                unrealized_pnl = (current_price - avg_price) * abs(net_qty)
            else:
                unrealized_pnl = (avg_price - current_price) * abs(net_qty)
        
        # R-Multiple
        r_multiple = 0.0
        if initial_risk and initial_risk != 0:
            # Gross PnL / Risk
            r_multiple = (realized_pnl + unrealized_pnl) / initial_risk

        # Days Held (Timezone Safe)
        days_held = 0
        if first_entry_time:
            # Decide end date
            if net_qty == 0 and last_tx_time:
                end_date = last_tx_time
            else:
                # Use current time, ensuring timezone compatibility
                now = datetime.now()
                end_date = now.astimezone() if first_entry_time.tzinfo else now
            
            # Safety: Ensure both are compatible regarding timezone
            if end_date.tzinfo is None and first_entry_time.tzinfo is not None:
                end_date = end_date.replace(tzinfo=first_entry_time.tzinfo)
            elif end_date.tzinfo is not None and first_entry_time.tzinfo is None:
                # Naive to Aware is tricky, try to assume local or remove tz from other
                first_entry_time = first_entry_time.replace(tzinfo=end_date.tzinfo)
                
            days_held = (end_date - first_entry_time).days

        return TradeMetrics(
            net_quantity=round(net_qty, 8),
            avg_price=round(avg_price, 4),
            unrealized_pnl=round(unrealized_pnl, 2),
            realized_pnl=round(realized_pnl, 2),
            total_commissions=round(total_commissions, 2),
            initial_risk=initial_risk,
            r_multiple=round(r_multiple, 2),
            days_held=days_held
        )

    @staticmethod
    def calculate_slippage(trigger_price: Optional[float], execution_price: float, quantity: float) -> float:
        """
        Calculates execution slippage.
        Negative result = Bad execution (Paid more / Sold for less).
        Positive result = Price Improvement.
        
        trigger_price: Limit price or Stop trigger.
        quantity: Signed quantity of the fill (+ for Buy, - for Sell).
        """
        if not trigger_price or trigger_price <= 0:
            return 0.0
            
        # Logic:
        # Buy (Qty > 0):  Expected/Limit 100, Exec 101 => Bad (-1)
        # Sell (Qty < 0): Expected/Limit 100, Exec 99 => Bad (-1)
        
        if quantity > 0:
            # Buying: Higher execution is BAD
            return trigger_price - execution_price
        else:
            # Selling: Lower execution is BAD
            return execution_price - trigger_price
