"""
py_market_data/manager.py
Core ChartManager Logic.
"""
import os
from typing import List, Optional
from datetime import datetime, timedelta

from py_tradeobject.interface import IMarketDataProvider, BarData
from .storage import load_bars, save_bars
from .utils import is_stale

class ChartManager:
    def __init__(self, storage_root: str, provider: Optional[IMarketDataProvider] = None):
        """
        Args:
            storage_root: Path where {ticker}/charts/{timeframe}.json will be stored.
            provider: Optional provider. If None, acts as Read-Only cache (or fails on stale).
        """
        self.storage_root = os.path.abspath(storage_root)
        self.provider = provider
        
    def ensure_data(self, ticker: str, timeframe: str, lookback: str = "1Y") -> List[BarData]:
        """
        Central access method [F-DATA-050].
        1. Checks Disk Cache.
        2. Checks Staleness.
        3. Fetches & Updates if needed (and provider available).
        4. Returns Data.
        """
        # 1. Path Resolution
        # Structure: {storage_root}/{ticker}/charts/{timeframe}.json
        # Normalize tf string? Let's assume passed strictly for now.
        chart_path = os.path.join(self.storage_root, ticker, "charts", f"{timeframe}.json")
        
        # 2. Load Existing
        bars = load_bars(chart_path)
        
        # 3. Check Staleness
        stale = False
        if not bars:
            stale = True # Empty is stale
        else:
            last_bar = bars[-1]
            stale = is_stale(last_bar.timestamp, timeframe)
            
        # 4. Fetch & Update if Stale
        if stale and self.provider:
            try:
                # Smart Lookback: If we have data, only request Delta
                fetch_lookback = lookback
                if bars:
                    fetch_lookback = self._get_smart_duration(bars[-1].timestamp)
                
                new_bars = self._fetch_and_merge(ticker, timeframe, fetch_lookback, bars)
                
                # Save if we got data
                if new_bars:
                    # save_bars handles normalization, deduplication (last wins), and sorting
                    bars = save_bars(chart_path, new_bars, timeframe=timeframe)
            except Exception as e:
                # Graceful degradation: print warning and keep cached bars
                print(f"  [ChartManager] Warning: Could not update {ticker} ({timeframe}): {e}")
                # We return whatever we have (or empty list)
        
        return bars

    def _get_smart_duration(self, last_bar_timestamp: datetime) -> str:
        """
        Calculates the required duration string (IBKR format) to fill the gap
        since the last bar.
        """
        now = datetime.now()
        delta = now - last_bar_timestamp
        
        # Security Buffer +1 Day
        days_needed = delta.days + 1
        
        # Minimum 1 Day request for IBKR
        if days_needed < 1:
            days_needed = 1
            
        return f"{days_needed} D"

    def _fetch_and_merge(self, ticker: str, timeframe: str, lookback: str, existing_bars: List[BarData]) -> List[BarData]:
        """
        Fetched new data and returns a combined list.
        Deduplication and sorting happens in save_bars().
        """
        # 1. Fetch
        incoming_bars = self.provider.get_historical_data(ticker, timeframe, lookback)
        if not incoming_bars:
            return existing_bars
            
        # 2. Simple Concatenation
        # save_bars() will handle the deduplication and sorting.
        return existing_bars + incoming_bars
