# py_riskmanager/minervini.py
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

@dataclass
class TradeParameters:
    symbol: str
    entry_price: float
    stop_loss: float
    risk_pct: float = 1.0       # Risk per Trade (e.g. 1% of Equity)
    max_pos_pct: float = 25.0   # Max Position Size (e.g. 25% of Equity)
    target_exposure: float = 100.0 # Target total exposure

@dataclass
class SizingContext:
    total_equity: float
    available_cash: float
    current_exposure: float

@dataclass
class SizingResult:
    symbol: str
    suggested_shares: int
    bottleneck: str # RISK, SIZE_CAP, CASH
    risk_amount: float
    risk_percent_equity: float
    position_size: float
    position_percent_equity: float
    scenarios: Dict[str, float]
    warnings: List[str]

class MinerviniSizer:
    """
    Calculates position size based on Minervini principles:
    1. Risk per Trade (R)
    2. Max Position Size (Cap)
    3. Available Cash
    """

    def calculate_sizing(self, ctx: SizingContext, params: TradeParameters) -> SizingResult:
        warnings = []
        
        if params.entry_price <= 0 or params.stop_loss <= 0:
            return self._error_result(params, "Invalid Price")
            
        if params.entry_price <= params.stop_loss:
             return self._error_result(params, "Entry must be > Stop (Long Only)")

        risk_per_share = params.entry_price - params.stop_loss
        stop_distance_pct = (risk_per_share / params.entry_price) * 100.0
        
        if stop_distance_pct < 1.0:
            warnings.append(f"Tight Stop: {stop_distance_pct:.2f}%")
        elif stop_distance_pct > 10.0:
            warnings.append(f"Wide Stop: {stop_distance_pct:.2f}% (Minervini prefers < 8-10%)")

        max_risk_amount = ctx.total_equity * (params.risk_pct / 100.0)
        shares_by_risk = int(max_risk_amount / risk_per_share)
        
        max_position_val = ctx.total_equity * (params.max_pos_pct / 100.0)
        shares_by_cap = int(max_position_val / params.entry_price)
        
        shares_by_cash = int(ctx.available_cash / params.entry_price)
        
        suggested_shares = min(shares_by_risk, shares_by_cap, shares_by_cash)
        bottleneck = "RISK"
        
        if suggested_shares == shares_by_cap and shares_by_cap < shares_by_risk:
            bottleneck = "SIZE_CAP"
        elif suggested_shares == shares_by_cash and shares_by_cash < shares_by_risk and shares_by_cash < shares_by_cap:
            bottleneck = "CASH/BUDGET"
            
        if suggested_shares < 1:
            warnings.append("Suggested shares < 1. Insufficient Equity or Risk.")
            suggested_shares = 0

        position_size = suggested_shares * params.entry_price
        actual_risk = suggested_shares * risk_per_share
        
        return SizingResult(
            symbol=params.symbol,
            suggested_shares=suggested_shares,
            bottleneck=bottleneck,
            risk_amount=round(actual_risk, 2),
            risk_percent_equity=round((actual_risk / ctx.total_equity) * 100, 2) if ctx.total_equity > 0 else 0,
            position_size=round(position_size, 2),
            position_percent_equity=round((position_size / ctx.total_equity) * 100, 2) if ctx.total_equity > 0 else 0,
            scenarios={
                "breakeven": round(params.entry_price * 1.002, 2),
                "target_2r": round(params.entry_price + (2 * risk_per_share), 2),
                "target_3r": round(params.entry_price + (3 * risk_per_share), 2)
            },
            warnings=warnings
        )

    def _error_result(self, params, msg) -> SizingResult:
        return SizingResult(params.symbol, 0, "ERROR", 0, 0, 0, 0, {}, [msg])
