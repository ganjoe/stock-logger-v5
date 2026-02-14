import math
import statistics
from typing import List
from .models import SeriesMetrics

def calculate_drawdown_series(equity_curve: List[float]) -> List[float]:
    """ 
    F-MATH-040: Returns list of DD% for each point (High Watermark). 
    DD = (HighWatermark - Current) / HighWatermark
    """
    if not equity_curve: return []
    
    drawdowns = []
    peak = equity_curve[0]
    
    for val in equity_curve:
        if val > peak:
            peak = val
        
        dd = 0.0
        if peak > 0:
            dd = (peak - val) / peak
        
        drawdowns.append(dd)
        
    return drawdowns

def calculate_series_metrics(equity_curve: List[float], periods_per_year: int = 252) -> SeriesMetrics:
    """ 
    F-MATH-050: Calc Total Return, CAGR, MaxDD, Volatility.
    Assumes daily data (periods_per_year=252) by default.
    """
    if not equity_curve or len(equity_curve) < 2:
        return SeriesMetrics(0,0,0,0,0,0)
        
    start_val = equity_curve[0]
    end_val = equity_curve[-1]
    
    # 1. Total Return
    total_return_pct = 0.0
    if start_val != 0:
        total_return_pct = (end_val - start_val) / start_val
        
    # 2. Max Drawdown
    dd_series = calculate_drawdown_series(equity_curve)
    max_dd_pct = max(dd_series) if dd_series else 0.0
    
    # 3. CAGR
    # (End/Start)^(1/Years) - 1
    # Years = len / 252
    years = len(equity_curve) / periods_per_year
    cagr = 0.0
    if start_val > 0 and end_val > 0 and years > 0:
        try:
            cagr = (end_val / start_val) ** (1 / years) - 1
        except:
            cagr = 0.0
            
    # 4. Volatility (Annualized Standard Deviation of Returns)
    returns = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i-1]
        curr = equity_curve[i]
        if prev != 0:
            r = (curr - prev) / prev
            returns.append(r)
            
    volatility = 0.0
    if len(returns) > 1:
        daily_std = statistics.stdev(returns)
        volatility = daily_std * math.sqrt(periods_per_year)
        
    # 5. Sharpe Ratio (Assume Risk Free = 0 for simplicity)
    # (CAGR - Rf) / Volatility? Or AvgReturn / StdDev?
    # Usually Avg Annual Return / Annual Volatility.
    # Let's use CAGR / Volatility as estimation.
    sharpe = 0.0
    if volatility > 0:
        sharpe = cagr / volatility
        
    # 6. Calmar Ratio (CAGR / MaxDD)
    calmar = 0.0
    if max_dd_pct > 0:
        calmar = cagr / max_dd_pct
        
    return SeriesMetrics(
        total_return_pct=total_return_pct,
        cagr=cagr,
        max_drawdown_pct=max_dd_pct,
        volatility=volatility,
        sharpe_ratio=sharpe,
        calmar_ratio=calmar
    )
