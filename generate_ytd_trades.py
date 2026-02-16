
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict

# Adjust path if needed or run from root
import sys
sys.path.append(".")

from py_tradeobject.core import TradeObject
from py_tradeobject.models import TradeStatus, TradeTransaction, TransactionType, TradeOrderLog

# --- CONFIG ---
TICKERS = ['AAPL', 'NVDA', 'TSLA', 'AMD', 'MSFT', 'META', 'GOOGL', 'AMZN', 'NFLX', 'SPY']
START_DATE = datetime(2025, 1, 1) # Assume current year or 2025 as base
ACTIONS_COUNT = 50
MIN_TRADE_DURATION = 5  # Days
MAX_TRADE_DURATION = 15 # Days

def random_date(start, end):
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return start + timedelta(seconds=random_second)

def create_trade_history():
    print(f"Generating {ACTIONS_COUNT} actions for YTD...")
    
    # Track open trades to manage exits/flips
    # Key: Ticker -> TradeObject
    active_trades: Dict[str, TradeObject] = {}
    
    # Store all generated actions to execute in chronological order?
    # Or just iterate through time?
    # Let's iterate day by day from Jan 1st to Now.
    
    current_date = START_DATE
    end_date = datetime.now()
    
    # We want ~50 actions.
    # Total days approx 45 (if we seek to 'now' in Feb 2025).
    # Action probability per day?
    
    total_actions = 0
    
    # Pre-calculate a timeline of potential events?
    # Let's just loop and act randomly.
    
    while current_date < end_date and total_actions < ACTIONS_COUNT:
        # Move forward 1 day (skip weekends mostly)
        current_date += timedelta(days=1)
        if current_date.weekday() >= 5: continue
        
        # Random logic
        if random.random() < 0.3: # 30% chance of action today
            
            # Decide Action Type
            # 1. Open New (if not active)
            # 2. Close Active
            # 3. Partial / Adjust Stop
            
            ticker = random.choice(TICKERS)
            
            if ticker not in active_trades:
                # OPEN NEW
                # Long or Short?
                direction = "LONG" if random.random() > 0.3 else "SHORT"
                price = random.uniform(100, 1000)
                qty = int(10000 / price) # Roughly $10k position
                
                trade = TradeObject(ticker=ticker) # Fresh
                trade._state.status = TradeStatus.OPEN
                trade._state.entry_date = current_date
                
                # Transaction
                tx = TradeTransaction(
                    id=str(uuid.uuid4()),
                    timestamp=current_date,
                    type=TransactionType.ENTRY,
                    quantity=float(qty) if direction == "LONG" else float(-qty),
                    price=price,
                    commission=1.0,
                    slippage=0.0
                )
                trade._state.transactions.append(tx)
                
                # Order Log (Entry)
                log_entry = TradeOrderLog(
                    timestamp=current_date,
                    order_id=f"oid_{ticker}_{total_actions}",
                    action="BUY" if direction == "LONG" else "SELL",
                    status="FILLED",
                    message="Initial Entry",
                    quantity=tx.quantity,
                    type="MKT",
                    limit_price=None,
                    stop_price=None,
                    note="Generated Entry"
                )
                trade._state.order_history.append(log_entry)
                
                # Stop Loss (Simulated Order)
                stop_price = price * 0.95 if direction == "LONG" else price * 1.05
                trade._state.initial_stop_price = stop_price
                trade._state.current_stop_price = stop_price
                
                log_stop = TradeOrderLog(
                    timestamp=current_date,
                    order_id=f"oid_{ticker}_{total_actions}_stop",
                    action="SELL" if direction == "LONG" else "BUY",
                    status="SUBMITTED",
                    message="Initial Stop",
                    quantity=-tx.quantity,
                    type="STP",
                    limit_price=None,
                    stop_price=stop_price,
                    note="Protection"
                )
                trade._state.active_orders[log_stop.order_id] = "STOP"
                trade._state.order_history.append(log_stop)
                
                active_trades[ticker] = trade
                print(f"[{current_date.date()}] OPEN {direction} {ticker} @ {price:.2f}")
                total_actions += 1
                
            else:
                # EXISTING TRADE
                trade = active_trades[ticker]
                duration = (current_date - trade._state.entry_date).days
                
                # Decide: Close, Partial, or Adjust Stop?
                action_roll = random.random()
                
                if duration > MAX_TRADE_DURATION or action_roll < 0.2:
                    # CLOSE (Full Exit)
                    last_price = trade._state.transactions[-1].price
                    exit_price = last_price * random.uniform(0.9, 1.1)
                    
                    # Calculate remaining qty
                    net_qty = sum(t.quantity for t in trade._state.transactions)
                    
                    if net_qty != 0:
                        tx = TradeTransaction(
                            id=str(uuid.uuid4()),
                            timestamp=current_date,
                            type=TransactionType.EXIT,
                            quantity=-net_qty, # Flatten
                            price=exit_price,
                            commission=1.0,
                            slippage=0.0
                        )
                        trade._state.transactions.append(tx)
                        
                        log_exit = TradeOrderLog(
                            timestamp=current_date,
                            order_id=f"oid_{ticker}_{total_actions}_exit",
                            action="SELL" if net_qty > 0 else "BUY",
                            status="FILLED",
                            message="Full Exit",
                            quantity=-net_qty,
                            type="MKT",
                            limit_price=None, 
                            stop_price=None,
                            note="Generated Exit"
                        )
                        trade._state.order_history.append(log_exit)
                        
                        trade._state.status = TradeStatus.CLOSED
                        trade._state.active_orders.clear() # Remove stop
                        
                        del active_trades[ticker]
                        print(f"[{current_date.date()}] CLOSE {ticker} @ {exit_price:.2f}")
                        total_actions += 1
                        
                elif action_roll < 0.5:
                    # PARTIAL EXIT
                    last_price = trade._state.transactions[-1].price
                    exit_price = last_price * random.uniform(0.95, 1.05)
                    net_qty = sum(t.quantity for t in trade._state.transactions)
                    
                    if abs(net_qty) > 10: # Only if enough shares
                        partial_qty = int(net_qty * 0.5) # Close half
                        
                        tx = TradeTransaction(
                            id=str(uuid.uuid4()),
                            timestamp=current_date,
                            type=TransactionType.EXIT,
                            quantity=-partial_qty,
                            price=exit_price,
                            commission=1.0,
                            slippage=0.0
                        )
                        trade._state.transactions.append(tx)
                        print(f"[{current_date.date()}] PARTIAL {ticker} ({partial_qty}) @ {exit_price:.2f}")
                        total_actions += 1
                        
                elif action_roll < 0.7:
                     # ADJUST STOP (Trail)
                     # If Long, raise stop if price up?
                     # Simulating price action logic... simplified.
                     original_stop = trade._state.current_stop_price
                     if original_stop:
                         new_stop = original_stop * 1.02 # Raise 2% (assuming Long for simplicity)
                         trade._state.current_stop_price = new_stop
                         
                         log_adj = TradeOrderLog(
                            timestamp=current_date,
                            order_id=f"oid_{ticker}_{total_actions}_adj",
                            action="Adjust",
                            status="SUBMITTED",
                            message="Trail Stop",
                            quantity=0,
                            type="STP",
                            limit_price=None,
                            stop_price=new_stop,
                            note="Trail"
                        )
                         trade._state.order_history.append(log_adj)
                         print(f"[{current_date.date()}] TRAIL STOP {ticker} -> {new_stop:.2f}")
                         total_actions += 1

        # Save updates
        for t in active_trades.values():
            t.save()
            
    # Cleanup: Ensure any remaining open trades are saved
    print("Saving final states...")
    for t in active_trades.values():
        t.save()
        
    print(f"\n[DONE] Generated {total_actions} actions YTD.")

if __name__ == "__main__":
    create_trade_history()
