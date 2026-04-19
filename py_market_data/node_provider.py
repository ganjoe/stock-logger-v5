"""
py_market_data/node_provider.py
Provider for accessing the external Parquet-based Data Node.
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List

from py_tradeobject.interface import IMarketDataProvider, BarData

class DataNodeProvider(IMarketDataProvider):
    """
    Reads historical data directly from the external stock-data-node
    Parquet database. Replaces the local archiving mechanisms.
    """
    def __init__(self, data_dir: str = "/home/daniel/stock-data-node/data/parquet"):
        self.data_dir = os.path.abspath(data_dir)

    def get_historical_data(self, symbol: str, timeframe: str, lookback: str) -> List[BarData]:
        # Normalize the timeframe request
        tf_map = {
            "1 day": "1D",
            "1 D": "1D",
            "1D": "1D",
            "1 hour": "1H",
            "1 H": "1H",
            "1H": "1H",
            "5 mins": "5m",
            "5m": "5m"
        }
        mapped_tf = tf_map.get(timeframe, timeframe)
        
        file_path = os.path.join(self.data_dir, symbol.upper(), f"{mapped_tf}.parquet")
        
        if not os.path.exists(file_path):
            print(f"  [DataNode] Warning: No {mapped_tf} parquet data found for {symbol}")
            return []
            
        try:
            # 1. Load full parquet into memory
            df = pd.read_parquet(file_path)
            
            # 2. Parse lookback
            now = datetime.now()
            parts = lookback.split()
            if len(parts) == 2:
                amount, unit = int(parts[0]), parts[1].upper()
            else:
                amount, unit = 1, "Y" # Default 1Y

            if unit == "Y":
                start_date = now - timedelta(days=365 * amount)
            elif unit == "M":
                start_date = now - timedelta(days=30 * amount)
            elif unit == "D":
                start_date = now - timedelta(days=amount)
            else:
                start_date = now - timedelta(days=365) # Fallback
                
            # 3. Filter DataFrame
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df[df['timestamp'] >= pd.to_datetime(start_date)]
            
            # 4. Map to BarData
            bars = []
            for _, row in df.iterrows():
                bars.append(BarData(
                    timestamp=row['timestamp'].to_pydatetime() if pd.notnull(row['timestamp']) else datetime.now(),
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row['volume'])
                ))
            
            return bars
            
        except Exception as e:
            print(f"  [DataNode] Error loading data for {symbol}: {e}")
            return []

    def get_current_price(self, symbol: str) -> float:
        """
        The DataNode does not provide live quotes. 
        Live quotes should be routed to the Broker Adapter instead.
        """
        raise NotImplementedError("DataNodeProvider only serves historical data.")
