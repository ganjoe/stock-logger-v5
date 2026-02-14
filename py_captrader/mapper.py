"""
py_captrader/mapper.py
DTO Mapper (IBKR -> TradeObject). Pure Functions.
"""
from typing import Optional
from ib_insync import Fill, Trade, OrderStatus
from py_tradeobject.models import TradeTransaction, TransactionType, TradeStatus
from datetime import datetime

class IBKRMapper:
    """Utilities to map IBKR types to TradeObject types."""

    @staticmethod
    def map_execution_to_transaction(fill: Fill) -> TradeTransaction:
        """
        Maps an IBKR Fill (Execution + Commission) to a TradeTransaction.
        Logic F-CAP-110: Use execId as unique ID.
        """
        exec = fill.execution
        
        # 1. Quantity (Signed)
        # IBKR Executions have 'side' (BOT/SLD) and strictly positive 'shares'.
        # We need signed quantity for TradeObject logic.
        qty = float(exec.shares)
        if exec.side == 'SLD':  # Sell
            qty = -qty
            
        # 2. Heuristik für Typ (Besser als immer ENTRY)
        # Wenn wir orderRef Kontext nicht haben, raten wir:
        # Dies ist nicht perfekt (Short Entry ist auch Sell), aber lesbarer.
        tx_type = TransactionType.ENTRY # Default
        
        # 3. Commission Safety
        # Manchmal ist commissionReport None
        commission = 0.0
        if fill.commissionReport and fill.commissionReport.commission:
             commission = fill.commissionReport.commission

        return TradeTransaction(
            id=exec.execId,
            timestamp=exec.time, # ib_insync returns datetime
            type=tx_type,
            quantity=qty,
            price=float(exec.avgPrice),
            commission=commission,
            slippage=0.0 # Calculated later by Logic
        )

    @staticmethod
    def map_order_status(ib_status: str) -> str:
        """
        Maps IBKR status string to internal representation.
        (ApiPending, PendingSubmit, PreSubmitted -> OPENING/CLOSING logic handled in Adapter)
        """
        # This helper might be used to determine if an order is 'Active'
        pass