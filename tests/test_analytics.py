from datetime import datetime
from py_analytics.capture import SnapshotAnalyzer
from py_analytics.series import SeriesAnalyzer
from py_analytics.performance import PerformanceAnalyzer
from py_portfolio_state.objects import PortfolioSnapshot, PortfolioPosition, PortfolioOrder, TradeResult

def test_snapshot_analyzer():
    # Setup Snapshot
    # Position: Ticker A, Qty 100, Entry 100, Current 90.
    # Order: Stop at 80.
    pos = PortfolioPosition(
        ticker="AAA",
        quantity=100.0,
        avg_price=100.0,
        current_price=90.0,
        market_value=9000.0,
        unrealized_pnl=-1000.0
    )
    
    order = PortfolioOrder(
        ticker="AAA",
        order_id="ORD1",
        action="SELL",
        type="STP",
        qty=100.0,
        price=80.0, # Stop Price
        trade_id="T1"
    )
    
    snap = PortfolioSnapshot(
        timestamp=datetime(2025, 1, 1),
        cash=10000.0,
        equity=19000.0, # 10k cash + 9k pos
        positions=[pos],
        active_orders=[order],
        source="TEST"
    )
    
    # Run Analysis
    analyzer = SnapshotAnalyzer()
    report = analyzer.analyze(snap)
    
    # Check Summary
    s = report.summary
    assert s.equity == 19000.0
    
    # Check Positions
    assert report.positions[0].ticker == "AAA"
    
    # Check Risk (Current 90 - Stop 80) * 100 = 1000 risk exposure
    p = report.positions[0]
    assert p.risk_exposure == 1000.0
    # Heat: 1000 / 19000 = 5.26%
    assert abs(p.risk_pct - 5.26) < 0.1
    assert p.heat_warning == True # > 2.5%

def test_series_analyzer():
    # Series: 10k -> 11k -> 9k -> 12k
    s1 = PortfolioSnapshot(datetime(2025,1,1), 10000, 10000, [], [], "TEST")
    s2 = PortfolioSnapshot(datetime(2025,1,2), 10000, 11000, [], [], "TEST")
    s3 = PortfolioSnapshot(datetime(2025,1,3), 10000, 9000, [], [], "TEST")
    s4 = PortfolioSnapshot(datetime(2025,1,4), 10000, 12000, [], [], "TEST")
    
    analyzer = SeriesAnalyzer()
    report = analyzer.analyze_history([s1, s2, s3, s4])
    
    # Verify Series Points
    assert len(report.series) == 4
    
    # Check Exposure in Point 2 (11k Equity, 10k Cash -> ? Wait, constructor args were Cash, Equity)
    # s2 = PortfolioSnapshot(datetime(2025,1,2), 10000, 11000, ...)
    # Cash=10k, Equity=11k. Exposure = 1000.
    p2 = report.series[1]
    assert p2.cash == 10000.0
    assert p2.exposure == 1000.0
    
    # Check MaxDD: 11k -> 9k = -2k / 11k = -18.18%
    # Report metric should capture this
    metrics = report.performance
    assert abs(metrics["max_drawdown_pct"] - 0.1818) < 0.001
    
    # Verify Summary is from latest (s4)
    assert report.summary.equity == 12000.0

def test_performance_analyzer():
    # Trade 1: +100
    # Trade 2: -50
    t1 = TradeResult("A", "LONG", datetime.now(), datetime.now(), 10, 11, 10, 100.0, 0, 0, 1)
    t2 = TradeResult("B", "LONG", datetime.now(), datetime.now(), 10, 9, 10, -50.0, 0, 0, 1)
    
    analyzer = PerformanceAnalyzer()
    results = analyzer.analyze_trades([t1, t2])
    
    assert results["total_trades"] == 2
    assert results["winrate"] == 0.5
    assert results["profit_factor"] == 2.0 # 100 / 50
    assert results["avg_win"] == 100.0

if __name__ == "__main__":
    test_snapshot_analyzer()
    test_series_analyzer()
    test_performance_analyzer()
    print("Analytics Verification PASSED")
