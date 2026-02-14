
from py_financial_math.risk import calculate_position_size, calculate_risk_exposure, calculate_heat
from py_financial_math.series import calculate_drawdown_series, calculate_series_metrics
from py_financial_math.performance import calculate_trade_metrics

def test_position_sizing():
    # Account 100k, Risk 1%, Entry 100, Stop 90
    # RiskAmount = 1000. RiskPerShare = 10. Qty = 100.
    qty = calculate_position_size(100000, 0.01, 100.0, 90.0)
    assert qty == 100.0
    
    # Check invalid
    assert calculate_position_size(0, 0.01, 100, 90) == 0.0
    assert calculate_position_size(100000, 0.01, 100, 100) == 0.0 # Div by zero handling

def test_risk_exposure():
    # Qty 100, Curr 110, Stop 90 (Stop raised or initial?)
    # Risk is distance to stop * qty
    # abs(110-90) * 100 = 20 * 100 = 2000
    risk = calculate_risk_exposure(100, 110.0, 90.0)
    assert risk == 2000.0

def test_heat():
    # Open Risks: [1000, 500], Equity: 100000
    # Total Risk = 1500. Heat = 1.5%
    heat = calculate_heat([1000.0, 500.0], 100000.0)
    assert heat == 1.5

def test_drawdown_series():
    # Curve: 100 -> 110 -> 99 -> 120
    # DD:    0%  -> 0%  -> (110-99)/110=10% -> 0%
    curve = [100.0, 110.0, 99.0, 120.0]
    dds = calculate_drawdown_series(curve)
    assert len(dds) == 4
    assert dds[0] == 0.0
    assert dds[1] == 0.0
    assert abs(dds[2] - 0.1) < 0.0001
    assert dds[3] == 0.0

def test_series_metrics():
    # Curve: 100 -> 110 -> 121 (10% gains)
    # Total Return: 21%
    # CAGR (252 periods/year): huge because only 3 days.
    # Let's test basic calculation
    curve = [100.0, 110.0, 121.0]
    m = calculate_series_metrics(curve, periods_per_year=252)
    assert abs(m.total_return_pct - 0.21) < 0.0001
    assert m.max_drawdown_pct == 0.0
    
    # Volatility should be 0 because returns are constant (10%, 10%)?
    # Stdev([0.1, 0.1]) = 0.
    assert m.volatility == 0.0
    
def test_trade_metrics():
    # Wins: 100, 200. Loss: -50.
    # Total: 3. Winrate: 2/3 = 66%.
    # AvgWin: 150. AvgLoss: -50.
    # Payoff: 3.0.
    # Expectancy: (0.66*150) - (0.33*50) = 100 - 16.5 = 83.33
    pnl = [100.0, -50.0, 200.0]
    m = calculate_trade_metrics(pnl)
    
    assert m.total_trades == 3
    assert abs(m.winrate - 0.6666) < 0.001
    assert m.avg_win == 150.0
    assert m.avg_loss == -50.0
    assert m.payoff_ratio == 3.0
    assert m.profit_factor == 300.0 / 50.0 # 6.0
    
if __name__ == "__main__":
    test_position_sizing()
    test_risk_exposure()
    test_heat()
    test_drawdown_series()
    test_series_metrics()
    test_trade_metrics()
    print("Financial Math Tests PASSED")
