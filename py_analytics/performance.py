from typing import List, Dict, Any
from py_portfolio_state.objects import TradeResult
import py_financial_math.performance as perf_math

class PerformanceAnalyzer:
    """ F-ANA-060: Helper to analyze TradeResult lists. """
    
    def analyze_trades(self, trades: List[TradeResult]) -> Dict[str, Any]:
        if not trades:
            return {}
            
        # Extract PnLs (absolute $)
        pnl_list = [t.pnl_absolute for t in trades]
        
        # Calculate Metrics
        metrics = perf_math.calculate_trade_metrics(pnl_list)
        
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
