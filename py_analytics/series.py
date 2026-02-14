from typing import List, Dict, Any
from py_portfolio_state.objects import PortfolioSnapshot
from .models import AnalyticsReport, SeriesPoint, SummaryRow

import py_financial_math.series as perf_math
from .capture import SnapshotAnalyzer

class SeriesAnalyzer:
    """ F-ANA-040: The Binoculars. Analyzes a time series (History). """
    
    def analyze_history(self, snapshots: List[PortfolioSnapshot]) -> AnalyticsReport:
        if not snapshots:
            # Return empty report? Or raise?
            # Return empty structure.
            return AnalyticsReport(
                summary=SummaryRow(None, 0, 0, 0, 0, 0),
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
        
        # Add Performance Metrics (Optional, add to 'performance' dict or summary?)
        # F-ANA-050 says "Delegation to Math Core".
        # Let's calculate and put in 'performance' dict alongside Trade Stats?
        # Or just log it for now? Models might not have dedicated fields for Series Metrics.
        # Report has 'performance: Optional[Dict]'. Good place.
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
