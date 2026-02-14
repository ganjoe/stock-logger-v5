"""
py_tradeobject/models.py
Core Data Structures (DTOs/Enums). PURE DATA.
"""
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any

class TradeStatus(Enum):
    PLANNED = "PLANNED"   # No position, setup phase
    OPENING = "OPENING"   # Entry order sent, no fill yet
    OPEN = "OPEN"         # Active position (partial or full)
    CLOSING = "CLOSING"   # Exit order sent
    CLOSED = "CLOSED"     # Position flat, trade finished
    ARCHIVED = "ARCHIVED" # Historical record

class TransactionType(Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ADJUSTMENT = "ADJUSTMENT"

@dataclass
class TradeTransaction:
    """Immutable record of an executed order."""
    id: str             # Broker Execution ID
    timestamp: datetime
    type: TransactionType
    quantity: float     # Signed Value: + for Long-Buys/Short-Covers, - for Long-Sells/Short-Enters
    price: float        # Execution price
    commission: float
    slippage: float = 0.0 # [F-TO-130]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type.value,
            "quantity": self.quantity,
            "price": self.price,
            "commission": self.commission,
            "slippage": self.slippage
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TradeTransaction':
        return TradeTransaction(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            type=TransactionType(data["type"]),
            quantity=data["quantity"],
            price=data["price"],
            commission=data["commission"],
            slippage=data.get("slippage", 0.0)
        )

@dataclass
class TradeMetrics:
    """Calculated intrinsic metrics for a trade."""
    net_quantity: float = 0.0
    avg_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_commissions: float = 0.0
    initial_risk: float = 0.0
    r_multiple: float = 0.0
    days_held: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TradeMetrics':
        return TradeMetrics(**data)
    
@dataclass
class TradeState:
    """The full serializable state of a trade object."""
    id: str             # [F-TO-140] order_ref
    ticker: str
    status: TradeStatus # [F-TO-120]
    transactions: List[TradeTransaction] = field(default_factory=list)
    active_orders: Dict[str, str] = field(default_factory=dict) # {broker_oid: 'ENTRY'|'STOP'|'EXIT'} [F-TO-120]
    
    # Metadata
    initial_stop_price: Optional[float] = None
    current_stop_price: Optional[float] = None
    entry_date: Optional[datetime] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "status": self.status.value,
            "transactions": [t.to_dict() for t in self.transactions],
            "active_orders": self.active_orders,
            "initial_stop_price": self.initial_stop_price,
            "current_stop_price": self.current_stop_price,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "notes": self.notes
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TradeState':
        return TradeState(
            id=data["id"],
            ticker=data["ticker"],
            status=TradeStatus(data["status"]),
            transactions=[TradeTransaction.from_dict(t) for t in data.get("transactions", [])],
            active_orders=data.get("active_orders", {}),
            initial_stop_price=data.get("initial_stop_price"),
            current_stop_price=data.get("current_stop_price"),
            entry_date=datetime.fromisoformat(data["entry_date"]) if data.get("entry_date") else None,
            notes=data.get("notes", "")
        )
