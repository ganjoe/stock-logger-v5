"""
py_market_data/utils.py
Helper functions for date calculations and staleness logic.
"""
from datetime import datetime, timedelta, time

def is_stale(last_timestamp: datetime, timeframe: str) -> bool:
    """
    Determines if the cached data is stale based on the last bar's timestamp.
    
    Logic:
    - 1D (Daily): Stale if last_timestamp < Today 00:00.
    - 1H (Hourly): Stale if last_timestamp < Current Hour Start (or say 1 hour+ old).
    - 5m: Stale if last_timestamp < 5 mins ago.
    """
    now = datetime.now()
    
    if timeframe == "1D" or timeframe == "1 day":
        # Daily Stale Condition:
        # If last bar is from yesterday (or older), we need today's potential bar.
        # Check if last_timestamp date < today's date
        today_midnight = datetime.combine(now.date(), time.min)
        return last_timestamp < today_midnight
        
    elif timeframe in ["1H", "1 hour"]:
        # Hourly Stale Condition:
        # If last bar is older than 1 hour (simplified)
        # Better: If last bar's hour < current hour
        # Let's say we want to ensure we have the latest closed hour?
        # Or current developing hour? 
        # Requirement F-DATA-030 says "Intraday: Zeitstempel > 1 Periode alt"
        diff = now - last_timestamp
        return diff.total_seconds() > 3600
        
    elif timeframe in ["5m", "5 mins"]:
        diff = now - last_timestamp
        return diff.total_seconds() > 300
        
    else:
        # Default fallback for unknown timeframes
        # Assume it's stale to be safe
        return True
