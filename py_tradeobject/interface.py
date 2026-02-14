"""
py_tradeobject/interface.py
Abstract Contracts (Broker). CONTRACTS.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass
from .models import TradeTransaction

@dataclass
class BrokerUpdate:
    """Standardized response from broker updates."""
    new_fills: List[TradeTransaction]       # Completely new executions
    active_order_ids: List[str]             # List of currently open order IDs
    cancelled_order_ids: List[str]          # IDs of orders that are no longer active

class IBrokerAdapter(ABC):
    """
    Contract for broker interactions.
    Decoupled interface that TradeObject relies on.
    """
    
    @abstractmethod
    def place_order(self, order_ref: str, symbol: str, quantity: float, 
                   limit_price: Optional[float] = None, 
                   stop_price: Optional[float] = None) -> str:
        """
        Places order and validates tick size [F-BR-010].
        
        Args:
            order_ref: Unique TradeID to tag the order (for filtering updates).
            symbol: Ticker symbol.
            quantity: Signed quantity (+ Buy, - Sell).
            limit_price: Optional limit price. None = Market.
            stop_price: Optional stop trigger price. None = No Stop.
            
        Returns:
            str: Broker Order ID (oid).
        """
        pass

    @abstractmethod
    def get_updates(self, order_ref: str) -> BrokerUpdate:
        """
        Fetches fills and status updates filtered by order_ref.
        The Adapter is responsible for converting raw broker fills into TradeTransaction objects.
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancels a specific order."""
        pass
