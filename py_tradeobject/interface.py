"""
py_tradeobject/interface.py
Abstract Contracts. NOW SPLIT.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from .models import TradeTransaction

# --- Data Transfer Objects ---

@dataclass
class BrokerUpdate:
    new_fills: List[TradeTransaction]
    active_order_ids: List[str]
    cancelled_order_ids: List[str]

@dataclass
class BarData:
    """Standard OHLCV Bar for Charts."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

# --- The Split Interfaces ---

class IExecutionProvider(ABC):
    """Responsible for TRADING (Orders, Fills)."""
    
    @abstractmethod
    def place_order(self, order_ref: str, symbol: str, quantity: float, 
                   limit_price: Optional[float] = None, 
                   stop_price: Optional[float] = None) -> str:
        pass

    @abstractmethod
    def get_updates(self, order_ref: str) -> BrokerUpdate:
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        pass

class IMarketDataProvider(ABC):
    """Responsible for DATA (History, Quotes)."""

    @abstractmethod
    def get_historical_data(self, symbol: str, timeframe: str, lookback: str) -> List[BarData]:
        """
        Fetches historical OHLCV data.
        timeframe: '1 day', '1 hour', '5 mins'
        lookback: '1 Y', '1 M', '5 D'
        """
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        """Fetches latest known price (Snapshot)."""
        pass

# --- The Union Interface (Optional, for backward compatibility) ---
class IBrokerAdapter(IExecutionProvider, IMarketDataProvider):
    """Full broker capabilities."""
    
    @abstractmethod
    def get_account_summary(self) -> Dict[str, float]:
        """Returns key metrics like 'TotalCash', 'NetLiquidation'."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Any]:
        """Returns raw position objects (adapter specific or generic DTOs)."""
        pass

    @abstractmethod
    def get_all_open_orders(self) -> List[Any]:
        """Returns list of open orders (adapter specific)."""
        pass