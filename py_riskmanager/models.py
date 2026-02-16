from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class PositionRow:
    """ Flattened view of a position with risk metrics. """
    ticker: str
    qty: float
    entry_price: float
    current_price: float
    market_val: float
    unrealized_pnl: float
    
    # Risk Metrics
    stop_price: Optional[float]
    r_per_share: float # |Entry - Stop|
    risk_exposure: float # $ Risk (qty * r_per_share)
    risk_pct: float # % of Account Equity
    
    # Alerts
    is_stale: bool = False
    heat_warning: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

@dataclass
class SummaryRow:
    timestamp: datetime
    equity: float
    cash: float
    open_risk_total: float
    heat_index: float # Total Risk / Equity (as %)
    daily_pnl: float # Change from prev day or open? Series logic determines this.
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

@dataclass
class SeriesPoint:
    timestamp: datetime
    equity: float
    cash: float
    exposure: float # Market Value of Positions (Equity - Cash)
    drawdown_pct: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "equity": self.equity,
            "cash": self.cash,
            "exposure": self.exposure,
            "drawdown_pct": self.drawdown_pct
        }

@dataclass
class AnalyticsReport:
    """ Unified Container (F-ANA-010). """
    summary: SummaryRow
    positions: List[PositionRow]
    series: List[SeriesPoint] = field(default_factory=list)
    performance: Optional[Dict] = None # Trade Stats
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "positions": [p.to_dict() for p in self.positions],
            "series": [s.to_dict() for s in self.series],
            "performance": self.performance
        }
