from datetime import datetime
from typing import List, Optional

from py_portfolio_state.objects import PortfolioSnapshot, PortfolioPosition
import py_financial_math.risk as risk_math
import py_financial_math.core as core_math

from .models import AnalyticsReport, PositionRow, SummaryRow

class SnapshotAnalyzer:
    """ F-ANA-030: The Loupe. Analyzes a single point in time. """
    
    def analyze(self, snapshot: PortfolioSnapshot) -> AnalyticsReport:
        positions_rows: List[PositionRow] = []
        total_open_risk = 0.0
        
        # 1. Analyze Positions
        for pos in snapshot.positions:
            # Find Stop Price from Active Orders (if any)
            # Logic: Look for STP order with matching ticker.
            stop_price = None
            
            # Filter active orders for this ticker
            # Note: snapshot.active_orders contains PortfolioOrder objects
            ticker_orders = [o for o in snapshot.active_orders if o.ticker == pos.ticker]
            
            # Find Stop Order
            for o in ticker_orders:
                if o.type in ["STP", "TRAIL", "STP LMT"]:
                    # Use auxPrice (trigger) if available, or price field?
                    # PortfolioOrder has 'price'. For STP, this is usually the trigger.
                    # Use the highest stop for Longs?
                    if stop_price is None or o.price > stop_price:
                        stop_price = o.price
            
            # Calculate Risk
            r_per_share = 0.0
            risk_exposure = 0.0
            
            if stop_price is not None:
                # Use Math Module
                risk_exposure = risk_math.calculate_risk_exposure(pos.quantity, pos.current_price, stop_price)
                r_per_share = core_math.calculate_r_multiple(pos.avg_price, stop_price, pos.current_price)
            
            # Calculate Risk % of Equity
            risk_pct = risk_math.calculate_total_risk_percent(risk_exposure, snapshot.equity)
                
            row = PositionRow(
                ticker=pos.ticker,
                qty=pos.quantity,
                entry_price=pos.avg_price,
                current_price=pos.current_price,
                market_val=pos.market_value,
                unrealized_pnl=pos.unrealized_pnl,
                stop_price=stop_price,
                r_per_share=r_per_share,
                risk_exposure=risk_exposure,
                risk_pct=risk_pct,
                heat_warning=(risk_pct > 2.5) # Example threshold
            )
            
            positions_rows.append(row)
            total_open_risk += risk_exposure
            
        # 2. Build Summary
        heat_index = 0.0
        if snapshot.equity > 0:
            heat_index = risk_math.calculate_heat([p.risk_exposure for p in positions_rows], snapshot.equity)
            
        summary = SummaryRow(
            timestamp=snapshot.timestamp,
            equity=snapshot.equity,
            cash=snapshot.cash,
            open_risk_total=total_open_risk,
            heat_index=heat_index,
            daily_pnl=0.0 # Snapshot doesn't know prev day. Needs series context.
        )
        
        return AnalyticsReport(
            summary=summary,
            positions=positions_rows,
            series=[]
        )
