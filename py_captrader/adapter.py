"""
py_captrader/adapter.py
Execution Adapter (TradeObject <-> IBKRClient). Integration Point.
"""
from typing import Dict, Optional, List, Any
import math
from datetime import datetime

from ib_insync import Order, LimitOrder, MarketOrder, TagValue
from py_tradeobject.interface import IBrokerAdapter, BrokerUpdate, BarData
from py_tradeobject.models import TradeTransaction
from .client import IBKRClient
from .mapper import IBKRMapper

class CapTraderAdapter(IBrokerAdapter):
    """
    Implementation of IBrokerAdapter using the synchronous IBKRClient wrapper.
    Handles execution logic, caching, and mapping.
    """
    
    def __init__(self, client: IBKRClient):
        self.client = client
        if not self.client.is_connected():
            self.client.connect()
            
    def place_order(self, order_ref: str, symbol: str, quantity: float, 
                   limit_price: Optional[float] = None, 
                   stop_price: Optional[float] = None) -> str:
        """
        Places order and validates tick size [F-CAP-080].
        Sets orderRef to TradeID [F-CAP-050].
        Blocks until submitted.
        """
        if not quantity or quantity == 0:
            raise ValueError("Quantity must not be zero")
            
        # 1. Get Contract & Details (Cached via Client)
        contract = self.client.qualify_contract(symbol)
        if not contract:
            raise ValueError(f"Could not qualify contract for {symbol}")
            
        details = self.client.get_contract_details(contract)
        min_tick = details.minTick if details else 0.01

        # 2. Setup Order Logic
        # ib_insync uses 'BUY'/'SELL' and positive quantity by default, 
        # but LimitOrder/MarketOrder helpers handle action/qty based on sign logic if implicit?
        # Actually LimitOrder(action, totalQuantity, lmtPrice) needs explicit action.
        action = 'BUY' if quantity > 0 else 'SELL'
        total_qty = abs(quantity)
        
        # SMART Routing & Order Type Selection
        order = None
        
        if stop_price and limit_price:
            # Stop Limit Order
            # Order constructor is safest for complex types
            order = Order()
            order.action = action
            order.totalQuantity = total_qty
            order.orderType = 'STP LMT'
            order.lmtPrice = self._round_tick(limit_price, min_tick)
            order.auxPrice = self._round_tick(stop_price, min_tick) # Trigger Price
            
        elif stop_price:
             # Stop Market
            order = Order()
            order.action = action
            order.totalQuantity = total_qty
            order.orderType = 'STP'
            order.auxPrice = self._round_tick(stop_price, min_tick)
            
        elif limit_price:
            # Limit Order
            order = LimitOrder(action, total_qty, self._round_tick(limit_price, min_tick))
            
        else:
            # Market Order
            order = MarketOrder(action, total_qty)
            
        # 3. Critical: Set Order Reference
        order.orderRef = order_ref
        order.tif = 'GTC' # Default to Good-Till-Canceled
        
        print(f"  [CapTrader] Placing Order: {action} {total_qty} {symbol} @ {order.orderType} (Ref: {order_ref})")
        
        # 4. Submit Blocking
        trade = self.client.place_order(contract, order)
        
        # 5. Return Broker ID
        # Prefer orderId which is now filled by client
        return str(trade.order.orderId)

    def get_updates(self, order_ref: str) -> BrokerUpdate:
        """
        Fetches fills and status updates filtered by order_ref.
        [F-CAP-060]
        """
        # 1. Get Fills (All session fills)
        all_fills = self.client.get_fills() # list of Fill objects
        
        new_transactions = []
        # Filter Fills by orderRef
        for fill_obj in all_fills:
            # fill_obj is a Fill(contract, execution, commissionReport, time)
            exec = fill_obj.execution
            if exec.orderRef == order_ref:
                # Map to Transaction
                tx = IBKRMapper.map_execution_to_transaction(fill_obj)
                new_transactions.append(tx)
                
        # 2. Get Open Orders
        open_trades = self.client.get_open_orders()
        active_ids = []
        
        for trade in open_trades:
            if trade.order.orderRef == order_ref:
                # This order belongs to our trade and is active
                active_ids.append(str(trade.order.orderId))
                
        cancelled_ids = [] # Not explicitly supported via API return yet
        
        return BrokerUpdate(
            new_fills=new_transactions,
            active_order_ids=active_ids,
            cancelled_order_ids=cancelled_ids
        )

    def cancel_order(self, order_id: str) -> bool:
        """Cancels a specific order."""
        open_trades = self.client.get_open_orders()
        for trade in open_trades:
             if str(trade.order.orderId) == str(order_id) or str(trade.order.permId) == str(order_id):
                 self.client.ib.cancelOrder(trade.order)
                 return True
        return False

    def _round_tick(self, price: float, min_tick: float) -> float:
        """Rounds price to nearest valid tick size."""
        if min_tick <= 0: return price
        rounded = round(price / min_tick) * min_tick
        # Precision fix for floats
        return round(rounded, 10)

    # --- Implementation IMarketDataProvider ---

    def get_historical_data(self, symbol: str, timeframe: str, lookback: str) -> List[BarData]:
        # 1. Qualify Contract
        contract = self.client.qualify_contract(symbol)
        if not contract:
            raise ValueError(f"Unknown symbol: {symbol}")

        # 2. Map Timeframe/Lookback to IBKR syntax
        # TradeObject nutzt saubere Strings, IBKR ist eigenwillig.
        ib_bar_size = "1 day" # Default
        if timeframe == "1D": ib_bar_size = "1 day"
        elif timeframe == "1H": ib_bar_size = "1 hour"
        
        ib_duration = "1 Y" # Default
        if lookback == "1Y": ib_duration = "1 Y"
        elif lookback == "1M": ib_duration = "1 M"

        # 3. Call Client
        ib_bars = self.client.get_history(contract, ib_duration, ib_bar_size)

        # 4. Map to DTO
        result = []
        for b in ib_bars:
            ts = b.date
            if not isinstance(ts, datetime):
                # Convert date to datetime (Midnight)
                ts = datetime(ts.year, ts.month, ts.day)

            result.append(BarData(
                timestamp=ts,
                open=b.open,
                high=b.high,
                low=b.low,
                close=b.close,
                volume=float(b.volume)
            ))
            
        return result

    def get_current_price(self, symbol: str) -> float:
        contract = self.client.qualify_contract(symbol)
        if not contract:
            raise ValueError(f"Unknown symbol: {symbol}")
        return self.client.get_market_snapshot(contract)

    def get_account_summary(self) -> Dict[str, float]:
        """
        Maps IBKR AccountValues to simplified Dict.
        """
        raw = self.client.get_account_summary()
        result = {}
        for val in raw:
            # We care about 'TotalCashValue', 'NetLiquidation', 'GrossPositionValue'
            if val.tag in ['TotalCashValue', 'NetLiquidation', 'GrossPositionValue']:
                 try:
                     result[val.tag] = float(val.value)
                 except ValueError:
                     pass
        return result

    def get_positions(self) -> List[Any]:
        """Returns raw IBKR Position objects."""
        return self.client.get_positions()