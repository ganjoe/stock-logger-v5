from datetime import datetime
from typing import List, Optional

from py_portfolio_state.objects import PortfolioSnapshot, PortfolioPosition
import py_financial_math.risk as risk_math
import py_financial_math.core as core_math

from .models import AnalyticsReport, PositionRow, SummaryRow

class SnapshotAnalyzer:
    """ F-ANA-030: The Loupe. Analyzes a single point in time. """
    
    def analyze(self, snapshot: PortfolioSnapshot) -> AnalyticsReport:
        import pandas as pd
        
        # 1. Get DataFrames
        df_pos = snapshot.positions_df
        df_ord = snapshot.active_orders_df
        
        # 2. Extract Stop Prices from Orders
        # Find all stop-like orders
        stop_types = ["STP", "TRAIL", "STP LMT"]
        df_stops = df_ord[df_ord["type"].isin(stop_types)]
        
        # Group by ticker, get max price (most conservative stop for longs)
        # Note: If no stops exist, this results in an empty Series
        ticker_stops = df_stops.groupby("ticker")["price"].max().to_dict()
        
        # 3. Process Positions
        positions_rows: List[PositionRow] = []
        total_open_risk = 0.0
        
        for _, pos_row in df_pos.iterrows():
            ticker = pos_row["ticker"]
            stop_price = ticker_stops.get(ticker)
            
            # Calculate Risk
            risk_exposure = 0.0
            r_per_share = 0.0
            if stop_price is not None:
                risk_exposure = risk_math.calculate_risk_exposure(pos_row["quantity"], pos_row["current_price"], stop_price)
                r_per_share = core_math.calculate_r_multiple(pos_row["avg_price"], stop_price, pos_row["current_price"])
            
            risk_pct = risk_math.calculate_total_risk_percent(risk_exposure, snapshot.equity)
            
            positions_rows.append(PositionRow(
                ticker=ticker,
                qty=pos_row["quantity"],
                entry_price=pos_row["avg_price"],
                current_price=pos_row["current_price"],
                market_val=pos_row["market_value"],
                unrealized_pnl=pos_row["unrealized_pnl"],
                stop_price=stop_price,
                r_per_share=r_per_share,
                risk_exposure=risk_exposure,
                risk_pct=risk_pct,
                heat_warning=(risk_pct > 2.5)
            ))
            total_open_risk += risk_exposure
            
        # 4. Build Summary
        heat_index = 0.0
        if snapshot.equity > 0:
            heat_index = risk_math.calculate_heat([p.risk_exposure for p in positions_rows], snapshot.equity)
            
        summary = SummaryRow(
            timestamp=snapshot.timestamp,
            equity=snapshot.equity,
            cash=snapshot.cash,
            open_risk_total=total_open_risk,
            heat_index=heat_index,
            daily_pnl=0.0
        )
        
        return AnalyticsReport(
            summary=summary,
            positions=positions_rows,
            series=[]
        )
