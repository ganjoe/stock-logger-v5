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

def normalize_timestamp(dt: datetime, timeframe: str = "any") -> int:
    """Standardizes timestamp to Unix seconds (integer)."""
    return int(dt.timestamp())

def save_bars(path: str, bars: List[BarData], timeframe: str = "1D") -> List[BarData]:
    """
    Saves BarData list to JSON with compact keys.
    Enforces Unix Timestamp normalization, deduplication (last wins), and sorting.
    Returns the cleaned BarData list.
    """
    if not bars:
        return []

    # 1. Normalize and Deduplicate
    unique_map = {}
    for bar in bars:
        ts_unix = normalize_timestamp(bar.timestamp)
        # We store both the bar and the normalized unix timestamp for sorting
        unique_map[ts_unix] = bar
        
    # 2. Sort by unix timestamp
    sorted_keys = sorted(unique_map.keys())
    cleaned_bars = [unique_map[k] for k in sorted_keys]
        
    # 3. Serialize for saving
    data_to_save = []
    for bar in cleaned_bars:
        data_to_save.append({
            "t": normalize_timestamp(bar.timestamp),
            "o": bar.open,
            "h": bar.high,
            "l": bar.low,
            "c": bar.close,
            "v": bar.volume
        })

    # 4. Save
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data_to_save, f, separators=(',', ':')) # Minimal whitespace
        
    return cleaned_bars

def load_bars(path: str) -> List[BarData]:
    """
    Loads BarData list from compact JSON.
    Supports both legacy ISO strings and new Unix integer timestamps.
    """
    if not os.path.exists(path):
        return []
        
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            
        bars = []
        for row in data:
            raw_t = row["t"]
            # Flexible Parsing: Handle both int/float and string formats
            if isinstance(raw_t, (int, float)):
                dt = datetime.fromtimestamp(raw_t)
            else:
                # Fallback for ISO strings in legacy files
                dt = datetime.fromisoformat(raw_t)

            bars.append(BarData(
                timestamp=dt,
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
