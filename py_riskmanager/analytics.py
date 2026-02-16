from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd

from py_portfolio_state.objects import PortfolioSnapshot, PortfolioPosition
import py_financial_math.risk as risk_math
import py_financial_math.core as core_math
import py_financial_math.series as perf_math

from .models import AnalyticsReport, PositionRow, SummaryRow, SeriesPoint

class SnapshotAnalyzer:
    """ 
    F-ANA-030: The Loupe. Analyzes a single point in time. 
    Moved from py_analytics.capture
    """
    
    def analyze(self, snapshot: PortfolioSnapshot) -> AnalyticsReport:
        
        # 1. Get DataFrames
        df_pos = snapshot.positions_df
        df_ord = snapshot.active_orders_df
        
        # 2. Extract Stop Prices from Orders
        # Find all stop-like orders
        stop_types = ["STP", "TRAIL", "STP LMT"]
        # Ensure df_ord is not empty or handle it
        if df_ord.empty:
            df_stops = pd.DataFrame(columns=df_ord.columns)
        else:
            df_stops = df_ord[df_ord["type"].isin(stop_types)]
        
        # Group by ticker, get max price (most conservative stop for longs)
        # Note: If no stops exist, this results in an empty dict
        ticker_stops = {}
        if not df_stops.empty:
             ticker_stops = df_stops.groupby("ticker")["price"].max().to_dict()
        
        # 3. Process Positions
        positions_rows: List[PositionRow] = []
        total_open_risk = 0.0
        
        if not df_pos.empty:
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

class SeriesAnalyzer:
    """ 
    F-ANA-040: The Binoculars. Analyzes a time series (History). 
    Moved from py_analytics.series
    """
    
    def analyze_history(self, snapshots: List[PortfolioSnapshot]) -> AnalyticsReport:
        if not snapshots:
            # Return empty
            return AnalyticsReport(
                summary=SummaryRow(datetime.now(), 0, 0, 0, 0, 0),
                positions=[],
                series=[]
            )
            
        # 1. Sort by time
        sorted_snaps = sorted(snapshots, key=lambda x: x.timestamp)
        
        # 2. Extract Curves
        equity_curve = [s.equity for s in sorted_snaps]
        
        # 3. Calculate Drawdowns
        dd_series = perf_math.calculate_drawdown_series(equity_curve)
        
        # 4. Build Series Points
        series_points: List[SeriesPoint] = []
        for i, s in enumerate(sorted_snaps):
            # Exposure = Market Value of Positions = Equity - Cash
            exposure = s.equity - s.cash
            
            pt = SeriesPoint(
                timestamp=s.timestamp,
                equity=s.equity,
                cash=s.cash,
                exposure=exposure,
                drawdown_pct=dd_series[i]
            )
            series_points.append(pt)
            
        # 5. Analyze Latest State (The Loupe)
        latest_snap = sorted_snaps[-1]
        analyzer = SnapshotAnalyzer()
        report = analyzer.analyze(latest_snap)
        
        # 6. Enrich Report
        report.series = series_points
        
        # Add Performance Metrics
        metrics = perf_math.calculate_series_metrics(equity_curve)
        
        if report.performance is None:
            report.performance = {}
            
        report.performance.update({
            "total_return_pct": metrics.total_return_pct,
            "cagr": metrics.cagr,
            "max_drawdown_pct": metrics.max_drawdown_pct,
            "volatility": metrics.volatility,
            "sharpe_ratio": metrics.sharpe_ratio
        })
        
        
        return report

# --- Performance Analyzer (F-ANA-060) ---
# Moved from py_analytics.performance

from py_portfolio_state.objects import TradeResult
import py_financial_math.performance as perf_math_trade

class PerformanceAnalyzer:
    """ F-ANA-060: Helper to analyze TradeResult lists. """
    
    def analyze_trades(self, trades: List[TradeResult]) -> Dict[str, Any]:
        if not trades:
            return {}
            
        # Extract PnLs (absolute $)
        pnl_list = [t.pnl_absolute for t in trades]
        
        # Calculate Metrics
        metrics = perf_math_trade.calculate_trade_metrics(pnl_list)
        
        # Convert to dict
        return {
            "total_trades": metrics.total_trades,
            "winrate": metrics.winrate,
            "avg_win": metrics.avg_win,
            "avg_loss": metrics.avg_loss,
            "payoff_ratio": metrics.payoff_ratio,
            "profit_factor": metrics.profit_factor,
            "expectancy": metrics.expectancy,
            "sqn": metrics.sqn
        }
