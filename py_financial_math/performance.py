import math
from typing import List
from .models import TradeMetrics

def calculate_trade_metrics(pnl_list: List[float]) -> TradeMetrics:
    """ 
    F-MATH-060: Winrate, SQN, etc. 
    Accepts raw PnL values (absolute $).
    """
    total = len(pnl_list)
    if total == 0:
        return TradeMetrics(0,0,0,0,0,0,0,0)
        
    wins = [p for p in pnl_list if p > 0]
    losses = [p for p in pnl_list if p <= 0]
    
    winrate = len(wins) / total
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    
    # Payoff Ratio (Avg Win / Avg Loss)
    # Avoid div by zero. Avg Loss is usually negative or 0. Use absolute.
    abs_avg_loss = abs(avg_loss)
    payoff = 0.0
    if abs_avg_loss > 0:
        payoff = avg_win / abs_avg_loss
        
    # Expectancy = (Win% * AvgWin) - (Loss% * AbsAvgLoss)
    loss_rate = 1.0 - winrate
    expectancy = (winrate * avg_win) - (loss_rate * abs_avg_loss)
    
    # SQN = sqrt(N) * (Expectancy / StdDev(R))
    # Note: Expectancy here is in $. Ideally should be in R-multiples for SQN.
    # If we assume pnl_list IS R-multiples, this works perfectly. 
    # If pnl_list is $, SQN still works relative to $ variability.
    import statistics
    sqn = 0.0
    if total > 1:
        stdev = statistics.stdev(pnl_list)
        if stdev > 0:
            sqn = math.sqrt(total) * (expectancy / stdev)
            
    # Profit Factor = Gross Profit / Gross Loss
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = 0.0
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = 999.0 # Info value
        
    return TradeMetrics(
        winrate=winrate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        payoff_ratio=payoff,
        profit_factor=profit_factor,
        expectancy=expectancy,
        sqn=sqn,
        total_trades=total
    )
