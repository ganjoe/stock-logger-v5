from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SeriesMetrics:
    total_return_pct: float
    cagr: float
    max_drawdown_pct: float
    volatility: float
    sharpe_ratio: float
    calmar_ratio: float

@dataclass
class TradeMetrics:
    winrate: float
    avg_win: float
    avg_loss: float
    payoff_ratio: float
    profit_factor: float
    expectancy: float
    sqn: float # System Quality Number
    total_trades: int
