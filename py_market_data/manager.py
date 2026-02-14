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
            # Smart Lookback: If we have data, only request Delta
            fetch_lookback = lookback
            if bars:
                fetch_lookback = self._get_smart_duration(bars[-1].timestamp)
            
            new_bars = self._fetch_and_merge(ticker, timeframe, fetch_lookback, bars)
            
            # Save if we got data
            if new_bars:
                save_bars(chart_path, new_bars)
                bars = new_bars
        
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
        Fetched new data and merges it with existing.
        [F-DATA-080] Gap Handling / Append Strategy.
        """
        # Determine effective lookback?
        # If we have data, we might only need "1 M" instead of "1 Y".
        # But IBKR lookback strings are static. 
        # Strategy:
        # If existing data is robust, we could query shorter period.
        # But simplistic approach: Query requested lookback, then merge dict-based by timestamp.
        
        # 1. Fetch
        incoming_bars = self.provider.get_historical_data(ticker, timeframe, lookback)
        if not incoming_bars:
            return existing_bars # Keep old if fetch fails? Or return empty?
            
        # 2. Merge (Dict based on timestamp to dedup/overwrite)
        # Last write wins (Incoming overwrites existing)
        merged_map = {}
        for b in existing_bars:
            merged_map[b.timestamp] = b
            
        for b in incoming_bars:
            merged_map[b.timestamp] = b
            
        # 3. Sort back to list
        sorted_bars = sorted(merged_map.values(), key=lambda x: x.timestamp)
        return sorted_bars
