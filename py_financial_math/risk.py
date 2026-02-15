from typing import List

def calculate_position_size(account_size: float, risk_pct: float, entry_price: float, stop_price: float) -> float:
    """ 
    F-MATH-020: Calc max quantity based on risk.
    Formula: MaxLoss = Account * RiskPct
             RiskPerShare = abs(Entry - Stop)
             Qty = MaxLoss / RiskPerShare
    """
    if account_size <= 0: return 0.0
    if risk_pct <= 0: return 0.0
    
    risk_amount = account_size * risk_pct
    risk_per_share = abs(entry_price - stop_price)
    
    if risk_per_share == 0: return 0.0 # Avoid division by zero
    
    return risk_amount / risk_per_share

def calculate_risk_exposure(qty: float, current_price: float, stop_price: float) -> float:
    """ 
    F-MATH-030: Calc $ risk if stop is hit. 
    Formula: abs(Current - Stop) * Qty
    Note: Calculates risk based on CURRENT price vs STOP, i.e. "Open Risk".
    """
    return abs(current_price - stop_price) * abs(qty)
    
def calculate_heat(open_risks: List[float], equity: float) -> float:
    """ 
    F-MATH-070: Calc Portfolio Heat (Total Risk / Equity). 
    """
    if equity <= 0: return 0.0
    total_risk = sum(open_risks)
    return (total_risk / equity) * 100.0 # Return as percentage

def calculate_risk_per_share(entry_price: float, stop_loss: float) -> float:
    """Calculates risk amount per unit."""
    return abs(entry_price - stop_loss)

def calculate_total_risk_percent(total_risk_amount: float, total_equity: float) -> float:
    """Calculates risk as percentage of equity."""
    if total_equity <= 0:
        return 0.0
    return (total_risk_amount / total_equity) * 100.0
