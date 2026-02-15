import pandas as pd
from datetime import datetime
from py_portfolio_state.objects import PortfolioSnapshot, PortfolioPosition, PortfolioOrder

def test_snapshot_pandas_conversion():
    # 1. Setup Snapshot with dummy data
    pos1 = PortfolioPosition("AAPL", 10, 150.0, 160.0, 1600.0, 100.0)
    ord1 = PortfolioOrder("AAPL", "1", "SELL", "STP", 10, 140.0, "TRD-1")
    
    snap = PortfolioSnapshot(
        timestamp=datetime.now(),
        cash=5000.0,
        equity=6600.0,
        positions=[pos1],
        active_orders=[ord1]
    )
    
    # 2. Test positions_df
    df_pos = snap.positions_df
    assert isinstance(df_pos, pd.DataFrame)
    assert len(df_pos) == 1
    assert df_pos.iloc[0]["ticker"] == "AAPL"
    assert df_pos.iloc[0]["market_value"] == 1600.0
    
    # 3. Test active_orders_df
    df_ord = snap.active_orders_df
    assert isinstance(df_ord, pd.DataFrame)
    assert len(df_ord) == 1
    assert df_ord.iloc[0]["ticker"] == "AAPL"
    assert df_ord.iloc[0]["price"] == 140.0
    
    # 4. Empty Snapshot
    empty_snap = PortfolioSnapshot(datetime.now(), 0, 0)
    df_empty = empty_snap.positions_df
    assert len(df_empty) == 0
    assert "ticker" in df_empty.columns
    
    print("\n[SUCCESS] Pandas DataFrame Bridge Verified.")

if __name__ == "__main__":
    test_snapshot_pandas_conversion()
