"""
py_market_data/storage.py
Handles JSON serialization/deserialization with compact keys.
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from py_tradeobject.interface import BarData

# Compact Key Mapping
# t = timestamp
# o = open
# h = high
# l = low
# c = close
# v = volume

def save_bars(path: str, bars: List[BarData]):
    """
    Saves BarData list to JSON with compact keys.
    """
    data = []
    for bar in bars:
        # Convert datetime to ISO string YYYY-MM-DD (if daily) or full ISO?
        # Requirement F-DATA-060: "t": "2023-10-27" example suggests date string for daily.
        # But we need to support intraday too. ISO format is safest.
        ts_str = bar.timestamp.isoformat()
        
        row = {
            "t": ts_str,
            "o": bar.open,
            "h": bar.high,
            "l": bar.low,
            "c": bar.close,
            "v": bar.volume
        }
        data.append(row)
        
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, 'w') as f:
        json.dump(data, f, separators=(',', ':')) # Minimal whitespace

def load_bars(path: str) -> List[BarData]:
    """
    Loads BarData list from compact JSON.
    Returns empty list if file not found or error.
    """
    if not os.path.exists(path):
        return []
        
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            
        bars = []
        for row in data:
            bars.append(BarData(
                timestamp=datetime.fromisoformat(row["t"]),
                open=float(row["o"]),
                high=float(row["h"]),
                low=float(row["l"]),
                close=float(row["c"]),
                volume=float(row["v"])
            ))
        return bars
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error loading chart data from {path}: {e}")
        return []
