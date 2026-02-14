from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class PortfolioPosition:
    ticker: str
    quantity: float
    avg_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    trade_id: Optional[str] = None # Reference to TradeObject UUID

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PortfolioPosition':
        return PortfolioPosition(**data)

@dataclass
class PortfolioOrder:
    # Snapshot of an active order at time X
    ticker: str
    order_id: str
    action: str # BUY/SELL
    type: str # LMT/STP
    qty: float
    price: float # Limit or Stop price
    trade_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PortfolioOrder':
        return PortfolioOrder(**data)

@dataclass
class PortfolioSnapshot:
    timestamp: datetime
    cash: float
    equity: float
    positions: List[PortfolioPosition] = field(default_factory=list)
    active_orders: List[PortfolioOrder] = field(default_factory=list)
    
    # Metadata
    source: str = "LIVE" # or "HISTORY"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "cash": self.cash,
            "equity": self.equity,
            "positions": [p.to_dict() for p in self.positions],
            "active_orders": [o.to_dict() for o in self.active_orders],
            "source": self.source
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PortfolioSnapshot':
        return PortfolioSnapshot(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            cash=data["cash"],
            equity=data["equity"],
            positions=[PortfolioPosition.from_dict(p) for p in data.get("positions", [])],
            active_orders=[PortfolioOrder.from_dict(o) for o in data.get("active_orders", [])],
            source=data.get("source", "LIVE")
        )

@dataclass
class TradeResult:
    # Summary of a CLOSED trade
    ticker: str
    direction: str # LONG/SHORT
    entry_date: datetime
    exit_date: datetime
    entry_price: float
    exit_price: float
    qty: float
    pnl_absolute: float
    pnl_percent: float
    r_multiple: float
    duration_days: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "direction": self.direction,
            "entry_date": self.entry_date.isoformat(),
            "exit_date": self.exit_date.isoformat(),
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "qty": self.qty,
            "pnl_absolute": self.pnl_absolute,
            "pnl_percent": self.pnl_percent,
            "r_multiple": self.r_multiple,
            "duration_days": self.duration_days
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TradeResult':
        return TradeResult(
            ticker=data["ticker"],
            direction=data["direction"],
            entry_date=datetime.fromisoformat(data["entry_date"]),
            exit_date=datetime.fromisoformat(data["exit_date"]),
            entry_price=data["entry_price"],
            exit_price=data["exit_price"],
            qty=data["qty"],
            pnl_absolute=data["pnl_absolute"],
            pnl_percent=data["pnl_percent"],
            r_multiple=data["r_multiple"],
            duration_days=data["duration_days"]
        )
