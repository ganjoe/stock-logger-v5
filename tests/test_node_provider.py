import os
import pandas as pd
import pytest
from datetime import datetime
from py_market_data.node_provider import DataNodeProvider

@pytest.fixture
def temp_parquet_dir(tmp_path):
    # tmp_path is a pytest fixture providing a temporary directory
    data_dir = tmp_path / "parquet"
    ticker_dir = data_dir / "TEST_STOCK"
    ticker_dir.mkdir(parents=True)
    
    # Create dummy DataFrame
    df = pd.DataFrame({
        'timestamp': [datetime(2023, 1, 1), datetime(2023, 1, 2)],
        'open': [100.0, 101.0],
        'high': [102.0, 103.0],
        'low': [99.0, 100.0],
        'close': [101.0, 102.0],
        'volume': [1000, 1500]
    })
    
    # Save to parquet
    file_path = ticker_dir / "1D.parquet"
    df.to_parquet(file_path)
    
    return str(data_dir)

def test_node_provider_read(temp_parquet_dir):
    provider = DataNodeProvider(data_dir=temp_parquet_dir)
    
    # Using '10 Y' lookback to ensure we grab the 2023 data
    bars = provider.get_historical_data("TEST_STOCK", "1D", "10 Y")
    
    assert len(bars) == 2
    assert bars[0].open == 100.0
    assert bars[1].close == 102.0
    assert bars[0].timestamp.year == 2023

def test_node_provider_missing_ticker(temp_parquet_dir):
    provider = DataNodeProvider(data_dir=temp_parquet_dir)
    
    bars = provider.get_historical_data("NON_EXISTENT", "1D", "1 Y")
    assert len(bars) == 0

def test_node_provider_live_quote_raises(temp_parquet_dir):
    provider = DataNodeProvider(data_dir=temp_parquet_dir)
    with pytest.raises(NotImplementedError):
        provider.get_current_price("TEST_STOCK")
