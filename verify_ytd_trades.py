
import os
import sys
import glob
import json
from datetime import datetime

sys.path.append(".")
from py_tradeobject.core import TradeObject
from py_tradeobject.models import TradeStatus

def verify_trades():
    print("Verifying Simulated Trades in ./data/trades ...")
    print(f"{'TICKER':<8} {'STATUS':<10} {'ID':<38} {'QTY':<8} {'AVG_PX':<10} {'LAST_PX':<10} {'R_PNL':<12} {'U_PNL':<12} {'TOTAL_PNL':<12}")
    print("-" * 130)
    
    total_realized = 0.0
    total_unrealized = 0.0
    trade_count = 0
    
    # 1. Scan Directories
    # Structure: data/trades/{TICKER}/{ID}.json
    base_dir = "./data/trades"
    if not os.path.exists(base_dir):
        print("No data directory found.")
        return

    tickers = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    
    for ticker in sorted(tickers):
        ticker_path = os.path.join(base_dir, ticker)
        trade_files = glob.glob(os.path.join(ticker_path, "*.json"))
        
        for tf in trade_files:
            try:
                # Load Trade
                with open(tf, 'r') as f:
                    data = json.load(f)
                    
                # We can use TradeObject to load or just parse dict. 
                # Let's use TradeObject to leverage logic (metrics calc).
                # But TradeObject needs ID and Ticker.
                trade_id = data.get("id")
                if not trade_id: continue
                
                trade = TradeObject(ticker=ticker, id=trade_id)
                
                # Check if it has transactions
                if not trade._state.transactions:
                    continue
                    
                # Calculate Metrics
                # Proxy Current Price = Last Transaction Price (or 0 if closed? Logic handles it)
                last_price = trade._state.transactions[-1].price
                
                # We explicitly pass the last_price to calculate unrealized PnL 
                # for the current state snapshot.
                # metrics = trade.refresh(current_price=last_price) # REMOVED: Needs Broker
                
                from py_tradeobject.logic import TradeCalculator
                metrics = TradeCalculator.calculate_metrics(trade._state.transactions, current_price=last_price)
                
                # Output Row
                status = trade.status.value
                r_pnl = metrics.realized_pnl
                u_pnl = metrics.unrealized_pnl
                total_pnl = r_pnl + u_pnl
                
                print(f"{ticker:<8} {status:<10} {trade.id:<38} {metrics.net_quantity:<8.1f} {metrics.avg_price:<10.2f} {last_price:<10.2f} {r_pnl:<12.2f} {u_pnl:<12.2f} {total_pnl:<12.2f}")
                
                total_realized += r_pnl
                total_unrealized += u_pnl
                trade_count += 1
                
            except Exception as e:
                print(f"Error reading {tf}: {e}")

    print("-" * 130)
    print(f"SUMMARY ({trade_count} Trades)")
    print(f"Total Realized:   ${total_realized:,.2f}")
    print(f"Total Unrealized: ${total_unrealized:,.2f}")
    print(f"TOTAL PnL:        ${total_realized + total_unrealized:,.2f}")

if __name__ == "__main__":
    verify_trades()
