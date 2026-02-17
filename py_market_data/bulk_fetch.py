# py_market_data/bulk_fetch.py
# Async Bulk Market Data Downloader (Reader ID)

import os
import sys
import asyncio
import argparse
from typing import List
from datetime import datetime
from ib_insync import IB

# Adjust path to find modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from py_market_data.domain import HistoryRequest
from py_market_data.downloader import BulkDownloader

def get_all_tickers(trades_dir: str = "./data/trades", cache_dir: str = "./data/market_cache") -> List[str]:
    """Scans trades AND market_cache directories for ticker subfolders."""
    tickers = set()
    
    # 1. Scan Trades
    if os.path.exists(trades_dir):
        for name in os.listdir(trades_dir):
            if os.path.isdir(os.path.join(trades_dir, name)):
                tickers.add(name.upper())

    # 2. Scan Cache
    if os.path.exists(cache_dir):
        for name in os.listdir(cache_dir):
            if os.path.isdir(os.path.join(cache_dir, name)):
                tickers.add(name.upper())
                
    return sorted(list(tickers))

def parse_ticker_args(arg_list: List[str], default_duration: str) -> List[HistoryRequest]:
    """
    Parses arguments like ['AAPL', 'MSFT:10 D', 'NVO'] into HistoryRequests.
    """
    requests = []
    for arg in arg_list:
        parts = arg.split(':')
        symbol = parts[0].upper()
        duration = default_duration
        if len(parts) > 1:
            duration = parts[1].replace('_', ' ') # helper if spaces are tricky in CLI
        
        requests.append(HistoryRequest(symbol=symbol, duration=duration))
    return requests

async def main_async(ticker_args: List[str], client_id: int, port: int):
    print(f"📉 Async Bulk Fetch (ID: {client_id}, Port: {port})...")
    
    ib = IB()
    try:
        print(f"🔌 Connecting to IBKR (Async)...")
        await ib.connectAsync(host="127.0.0.1", port=port, clientId=client_id)
        print("✅ Connected.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # 1. Detect Permissions & Config
    downloader = BulkDownloader(ib, max_concurrent=1) # Initial instance
    config = await downloader.verify_market_data_type()
    
    # Update Downloader with Config Limits
    downloader.semaphore = asyncio.Semaphore(config.max_concurrent)
    downloader.pacing_delay = config.pacing_delay
    print(f"\n⚙️  Config: {config.description}")
    print(f"   - Concurrent: {config.max_concurrent}")
    print(f"   - Duration: {config.default_duration}")
    print(f"   - Pacing Delay: {config.pacing_delay}s")

    # 2. Unified Chunking Loop (Robust for 30 Years)
    # We iterate years backwards for ALL modes.
    
    symbols = []
    if ticker_args:
        for t in ticker_args:
            symbols.append(t.split(':')[0].upper())
    else:
        symbols = get_all_tickers()

    print(f"\n📚 Starting Smart History Build ({config.description})...")
    
    # [F-DATA-050] Pre-Scan Coverage to avoid redundant fetches
    print("🔍 Scanning existing coverage...")
    coverage_map = {}
    for s in symbols:
        coverage_map[s] = downloader.check_coverage(s)
        
    current_year = datetime.now().year
    start_year = current_year - 30
    
    total_batches = current_year - start_year + 1
    processed_batch = 0
    
    # Iterate years descending
    for year in range(current_year, start_year - 1, -1):
        processed_batch += 1
        end_date = f"{year}1231 23:59:59" 
        print(f"\n📅 Batch {processed_batch}/{total_batches}: Year {year}")
        
        # Create Requests for this year (Filter by Coverage)
        reqs = []
        skipped = 0
        for s in symbols:
            # If we already have this year fully covered, and it's not the current year (always update current)
            if year in coverage_map[s] and year != current_year:
                skipped += 1
                continue
            reqs.append(HistoryRequest(s, '1 Y', end_date=end_date))
            
        if not reqs:
            print(f"   -> Skipped (All {skipped} symbols have data).")
            continue
            
        print(f"   -> Fetching {len(reqs)} symbols ({skipped} skipped)...")
        
        # Execute Batch
        # Downloader handles concurrency/pacing details
        start_time = asyncio.get_event_loop().time()
        results = await downloader.run_batch(reqs)
        duration = asyncio.get_event_loop().time() - start_time
        
        # Report Brief
        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count
        print(f"   -> Result: {success_count}/{len(reqs)} OK in {duration:.2f}s")
        
        if fail_count > 0:
             # Print errors for this batch to see issues immediately
             for r in results:
                 if not r.success:
                     print(f"      ❌ {r.symbol}: {r.error_message}")
        
        # Slight breather between batches if needed?
        # Paid mode handles it fast. Free mode handles it slow.
        # We rely on downloader pacing.

    
    print("\n✅ All Done.")
    ib.disconnect()

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", type=int, default=999, help="Reader Client ID")
    parser.add_argument("--port", type=int, default=4002, help="Gateway Port")
    parser.add_argument("tickers", nargs="*", help="List of tickers.")
    args = parser.parse_args()
        
    asyncio.run(main_async(args.tickers, args.client_id, args.port))

if __name__ == "__main__":
    run()
