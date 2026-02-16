# py_market_data/domain.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class HistoryRequest:
    """Defines what to fetch for a ticker."""
    symbol: str
    duration: str  # e.g. '5 D', '33 D', '1 Y', '30 Y'
    bar_size: str = '1 day' 
    what_to_show: str = 'TRADES'
    duration: str  # e.g. '5 D', '33 D', '1 Y', '30 Y'
    bar_size: str = '1 day' 
    what_to_show: str = 'TRADES'
    use_rth: bool = True  # Regular Trading Hours
    end_date: str = ''   # Optional end date (YYYYMMDD HH:mm:ss)

@dataclass
class BatchDownloadResult:
    """Feedback on success or failure per ticker."""
    symbol: str
    success: bool
    data_points_count: int
    error_message: Optional[str] = None

@dataclass(frozen=True)
class BatchConfig:
    """Adaptive runtime configuration based on market data permissions."""
    market_data_type: int # 1=Live, 3=Delayed, 4=Frozen
    max_concurrent: int
    default_duration: str
    pacing_delay: float # seconds to sleep after each request
    description: str
