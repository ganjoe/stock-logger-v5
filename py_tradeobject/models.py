"""
py_tradeobject/models.py
Core Data Structures (DTOs/Enums). PURE DATA.
"""
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any

class TradeType(Enum):
    STOCK = "STOCK"       # Normal equity/stock trade
    CASH = "CASH"         # Deposit or Withdrawal (no broker interaction)

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
class TradeOrderLog:
    """
    Historical record of an order submission.
    Essential for analyzing 'Intended Risk' vs. 'Actual Outcome'.
    """
    timestamp: datetime
    order_id: str       # Broker ID
    action: str         # BUY / SELL
    status: str         # [NEW] SUBMITTED, FILLED, CANCELLED
    message: str        # [NEW] Log message
    quantity: float     # Signed or Unsigned? Let's keep it signed like transactions (+Buy/-Sell)
    type: str           # LMT, MKT, STP, STP LMT
    limit_price: Optional[float]
    stop_price: Optional[float]
    trigger_price: Optional[float] = None # For Stop Orders (auxPrice)
    note: str = ""      # e.g. "Initial Entry", "Stop Trail", "Scale Out"
    details: Dict[str, Any] = field(default_factory=dict) # [NEW] Extra details

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "order_id": self.order_id,
            "action": self.action,
            "status": self.status,
            "message": self.message,
            "quantity": self.quantity,
            "type": self.type,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "trigger_price": self.trigger_price,
            "note": self.note,
            "details": self.details
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TradeOrderLog':
        return TradeOrderLog(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            order_id=data["order_id"],
            action=data["action"],
            status=data.get("status", "UNKNOWN"),
            message=data.get("message", ""),
            quantity=data["quantity"],
            type=data["type"],
            limit_price=data.get("limit_price"),
            stop_price=data.get("stop_price"),
            trigger_price=data.get("trigger_price"),
            note=data.get("note", ""),
            details=data.get("details", {})
        )

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
    order_id: Optional[str] = None # Broker Order ID (for linking back to logs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type.value,
            "quantity": self.quantity,
            "price": self.price,
            "commission": self.commission,
            "slippage": self.slippage,
            "order_id": self.order_id
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
            slippage=data.get("slippage", 0.0),
            order_id=data.get("order_id")
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
    trade_type: TradeType = TradeType.STOCK  # [F-TO-170] STOCK or CASH
    transactions: List[TradeTransaction] = field(default_factory=list)
    active_orders: Dict[str, str] = field(default_factory=dict) # {broker_oid: 'ENTRY'|'STOP'|'EXIT'} [F-TO-120]
    
    # NEU: Das vollständige Order-Tagebuch
    order_history: List[TradeOrderLog] = field(default_factory=list)
    
    # Metadata
    initial_stop_price: Optional[float] = None
    current_stop_price: Optional[float] = None
    entry_date: Optional[datetime] = None
    notes: str = ""

    @property
    def is_cash(self) -> bool:
        """Convenience check: Is this a cash deposit/withdrawal?"""
        return self.trade_type == TradeType.CASH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "status": self.status.value,
            "trade_type": self.trade_type.value,
            "transactions": [t.to_dict() for t in self.transactions],
            "order_history": [o.to_dict() for o in self.order_history],
            "active_orders": self.active_orders,
            "initial_stop_price": self.initial_stop_price,
            "current_stop_price": self.current_stop_price,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "notes": self.notes
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TradeState':
        state = TradeState(
            id=data["id"],
            ticker=data["ticker"],
            status=TradeStatus(data["status"]),
            trade_type=TradeType(data.get("trade_type", "STOCK")),  # Backward compat
        )
        
        if "transactions" in data:
            state.transactions = [TradeTransaction.from_dict(t) for t in data["transactions"]]
            
        if "order_history" in data:
            state.order_history = [TradeOrderLog.from_dict(o) for o in data["order_history"]]
            
        if "active_orders" in data:
            state.active_orders = data["active_orders"]
            
        state.initial_stop_price = data.get("initial_stop_price")
        state.current_stop_price = data.get("current_stop_price")
        if data.get("entry_date"):
            state.entry_date = datetime.fromisoformat(data["entry_date"])
        state.notes = data.get("notes", "")
            
        return state
