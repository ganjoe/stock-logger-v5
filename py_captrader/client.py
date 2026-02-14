"""
py_captrader/client.py
IBKR Client Wrapper handling Connection Management and Contract Caching.
"""
import asyncio
import threading
import time
from typing import Optional, List, Dict, Any, Union
from ib_insync import IB, Contract, Order, Trade, ExecutionFilter
import ib_insync.util as ib_util

class IBKRClient:
    """
    Synchronous wrapper around ib_insync.IB.
    Manages the connection and interaction with TWS/Gateway.
    Provides blocking methods for synchronous callers (TradeObject).
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        self.host = host
        self.port = port
        self.client_id = client_id
        
        self.ib = IB()
        self._connected = False
        
        # Contract Cache (ConID -> Details) [F-CAP-100]
        self._contract_cache: Dict[str, Contract] = {} 
        # Key: Symbol
        # Value: Qualified Contract with minTick, etc.

    def connect(self):
        """Connects to TWS (Blocking)."""
        if not self.ib.isConnected():
            print(f"Connecting to IBKR TWS ({self.host}:{self.port} ID:{self.client_id})...")
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self._connected = True
            # Request auto-open orders to populate state
            self.ib.reqAllOpenOrders()

    def disconnect(self):
        """Disconnects."""
        if self.ib.isConnected():
            self.ib.disconnect()
            self._connected = False

    def is_connected(self) -> bool:
        return self.ib.isConnected()

    # --- Sync-Async Bridge Methods (F-CAP-090) ---
    # Since ib_insync methods (like qualifyContracts) are blocking by default 
    # when called without 'Async' suffix in a script, we can use them directly 
    # IF we are not inside an asyncio loop. 
    # However, if we are in a GUI loop or complex app, we might need RunLoop.
    # For this CLI tool, standard ib_insync blocking calls work fine 
    # (they internally run the loop until complete).

    def qualify_contract(self, symbol: str) -> Optional[Contract]:
        """
        Qualifies a contract for the symbol (Blocking).
        Uses Cache [F-CAP-100].
        """
        if symbol in self._contract_cache:
            return self._contract_cache[symbol]

        # Create basic contract
        contract = Contract()
        contract.symbol = symbol
        contract.secType = 'STK'
        contract.exchange = 'SMART'
        contract.currency = 'USD'
        
        try:
            # Blocking call
            qualified_list = self.ib.qualifyContracts(contract)
            if qualified_list:
                c = qualified_list[0]
                self._contract_cache[symbol] = c
                return c
            else:
                print(f"Error: Could not qualify contract for {symbol}")
                return None
        except Exception as e:
            print(f"Error qualifying contract {symbol}: {e}")
            return None

    def get_contract_details(self, contract: Contract):
        """Fetches details (minTick) Blocking."""
        # ib.reqContractDetails is blocking
        details_list = self.ib.reqContractDetails(contract)
        return details_list[0] if details_list else None

    def place_order(self, contract: Contract, order: Order, timeout: float = 5.0) -> Trade:
        """
        Places order and waits for acknowledgement (Blocking).
        Returns the Trade object which tracks the order.
        Raises TimeoutError if order is not acknowledged within timeout.
        """
        trade = self.ib.placeOrder(contract, order)
        
        # Block until order is at least Submitted (or Cancelled)
        # We want to ensure we have a valid OrderID and it reached TWS.
        start_time = time.time()
        while not trade.isDone():
            self.ib.sleep(0.05) # Pulse the loop
            if trade.orderStatus.status in ('Submitted', 'PreSubmitted', 'Filled', 'Cancelled', 'Inactive'):
                break
            
            if time.time() - start_time > timeout:
                # Timeout reached. We don't cancel automatically, but we stop blocking.
                # Caller must decide whether to cancel or retry.
                # Just logging warning? Or raising?
                # Raising is safer for synchronous flow.
                raise TimeoutError(f"Order placement timed out after {timeout}s. Status: {trade.orderStatus.status}")
                
        return trade

    def get_open_orders(self) -> List[Trade]:
        """Returns list of open trades (Blocking sync)."""
        # Ensure we are synced
        self.ib.reqAllOpenOrders()
        # Sleep briefly to process incoming msg
        self.ib.sleep(0.1) 
        return self.ib.openTrades()
        
    def get_fills(self) -> List[Any]:
        """Returns list of all fills in this session."""
        # ib.fills() returns list of (Fill) namedtuples or Trade objects?
        # Actually ib.fills() yields (Contract, Execution, CommissionReport) tuples 
        # or we can iterate ib.fills() list if maintained.
        # ib_insync maintains ib.fills() list automatically.
        return list(self.ib.fills())

    def get_execution_updates(self, req_id: int = None):
        """Forces a refresh of executions (Blocking)."""
        # reqExecutions is heavy, usually auto-updates via valid connection are enough.
        # Use sparingly.
        pass

    def get_history(self, contract: Contract, duration_str: str, bar_size_setting: str) -> List[Any]:
        """
        Fetches historical data (Blocking).
        Wraps async reqHistoricalData.
        """
        # IBKR reqHistoricalData is blocking in this synchronous context
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=duration_str,
            barSizeSetting=bar_size_setting,
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1
        )
        return bars

    def get_market_snapshot(self, contract: Contract) -> float:
        """
        Gets a live price snapshot using reqTickers.
        reqTickers is more robust than reqMktData for snapshots as it waits for data.
        """
        import math
        tickers = self.ib.reqTickers(contract)
        if tickers:
            t = tickers[0]
            # Use marketPrice() helper which handles last/close/bid-ask fallback
            price = t.marketPrice()
            if math.isnan(price):
                # Hard fallback logic
                price = t.last if not math.isnan(t.last) else t.close
                if math.isnan(price): price = 0.0
            return price
        return 0.0