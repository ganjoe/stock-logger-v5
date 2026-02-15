from typing import Union

def calculate_pnl(entry_price: float, exit_price: float, quantity: float) -> float:
    """
    Calculates absolute PnL.
    Supports both long (qty > 0) and short (qty < 0) positions.
    """
    return (exit_price - entry_price) * quantity

def calculate_r_multiple(entry_price: float, stop_loss: float, current_price: float) -> float:
    """
    Calculates R-Multiple of current price.
    Formula: (Current - Entry) / (Entry - Stop)
    """
    risk_per_share = entry_price - stop_loss
    if risk_per_share == 0:
        return 0.0
    
    return (current_price - entry_price) / risk_per_share
