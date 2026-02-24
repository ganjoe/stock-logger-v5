# py_market_data/bulk_fetch.py
# Async Bulk Market Data Downloader (Reader ID)

import os
import sys
import asyncio
import argparse
import json
from typing import List, Dict, Set, Optional
from datetime import datetime
from collections import defaultdict
from ib_insync import IB

# Adjust path to find modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from py_market_data.domain import HistoryRequest
from py_market_data.downloader import BulkDownloader

# Pseudo-tickers that must never be fetched from IBKR
SKIP_TICKERS = {"_CASH", "HIST_ORDER_TEST"}

TICKER_MAP_PATH = "./data/ticker_map.json"


class TickerMap:
    """
    Manages ticker symbol mappings for IBKR resolution.
    
    File format (data/ticker_map.json):
      {
        "4GLD": null,           // Auto-added, not yet mapped -> skip
        "4GLD": "4GLD:EUR",     // Mapped: fetch as 4GLD with EUR currency
        "VBTC": "VBTC:EUR",     // Mapped: fetch as VBTC with EUR currency
        "XDEF.DE": "XDEF:EUR:FWB2"  // Mapped: symbol:currency:exchange
      }
    
    Format: "IBKR_SYMBOL" or "IBKR_SYMBOL:CURRENCY" or "IBKR_SYMBOL:CURRENCY:EXCHANGE"
    Defaults: currency=USD, exchange=SMART
    """
    def __init__(self, path: str = TICKER_MAP_PATH):
        self.path = path
        self._map: Dict[str, Optional[str]] = {}
        self._load()
    
    def _load(self):
        """Loads the map from disk, creates empty file if missing."""
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    self._map = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._map = {}
        else:
            self._map = {}
    
    def _save(self):
        """Writes the map back to disk (sorted for readability)."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        sorted_map = dict(sorted(self._map.items()))
        with open(self.path, "w") as f:
            json.dump(sorted_map, f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def _parse_mapping(value: str) -> tuple:
        """
        Parses 'SYMBOL:CURRENCY:EXCHANGE' into (symbol, currency, exchange).
        Defaults: currency='USD', exchange='SMART'
        """
        parts = value.split(":")
        symbol = parts[0]
        currency = parts[1] if len(parts) > 1 else "USD"
        exchange = parts[2] if len(parts) > 2 else "SMART"
        return (symbol, currency, exchange)
    
    def resolve(self, ticker: str) -> Optional[tuple]:
        """
        Returns (ibkr_symbol, currency, exchange) for a ticker.
        - Not in map: return None (no override, use TradeObject data)
        - Mapped to a string: parse and return tuple
        - Mapped to null: return 'SKIP' sentinel
        """
        if ticker not in self._map:
            return None  # No override
        value = self._map[ticker]
        if value is None:
            return "SKIP"
        return self._parse_mapping(value)
    
    def register_failed(self, ticker: str):
        """
        Auto-registers a ticker that failed qualification.
        Only adds if not already in the map (don't overwrite manual mappings).
        """
        if ticker not in self._map:
            self._map[ticker] = None  # null = unmapped
            self._save()
    
    def get_unmapped_count(self) -> int:
        """Returns count of tickers with null mapping."""
        return sum(1 for v in self._map.values() if v is None)
    
    def get_mapped(self) -> Dict[str, str]:
        """Returns only the resolved mappings (non-null)."""
        return {k: v for k, v in self._map.items() if v is not None}

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
    
    # 3. Filter out pseudo-tickers
    filtered = tickers - SKIP_TICKERS
    skipped = tickers & SKIP_TICKERS
    if skipped:
        print(f"  ⏭️  Skipping non-stock tickers: {', '.join(sorted(skipped))}")
                
    return sorted(list(filtered))

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


class BulkFetchLogger:
    """
    Collects errors and successes during a bulk fetch run.
    Writes a structured JSON log file, updated after every batch.
    """
    LOG_PATH = "./data/bulk_fetch_log.json"

    def __init__(self):
        self.start_time = datetime.now()
        # {category: {symbol: [{"message": str, "year": int}]}}
        self.errors: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        # {symbol: total_bars_fetched}
        self.successes: Dict[str, int] = defaultdict(int)
        # Unique symbols that failed (deduplicated across years)
        self._failed_symbols: Set[str] = set()

    def record_error(self, symbol: str, category: str, message: str, year: int):
        """Records a categorized error for a symbol."""
        self.errors[category][symbol].append({
            "message": message,
            "year": year
        })
        self._failed_symbols.add(symbol)

    def record_success(self, symbol: str, data_points: int):
        """Records a successful fetch for a symbol."""
        self.successes[symbol] += data_points

    def write(self) -> str:
        """Writes/overwrites the log file. Returns the path."""
        os.makedirs(os.path.dirname(self.LOG_PATH), exist_ok=True)

        duration = (datetime.now() - self.start_time).total_seconds()

        # Build categorized symbol lists (deduplicated)
        categorized = {}
        for category, symbols in self.errors.items():
            categorized[category] = {
                "count": len(symbols),
                "symbols": sorted(symbols.keys()),
                "details": {sym: entries for sym, entries in sorted(symbols.items())}
            }

        log_data = {
            "run_info": {
                "timestamp": self.start_time.isoformat(),
                "duration_seconds": round(duration, 1),
                "total_symbols_attempted": len(self.successes) + len(self._failed_symbols),
                "total_success": len(self.successes),
                "total_failed": len(self._failed_symbols),
                "total_bars_fetched": sum(self.successes.values())
            },
            "errors_by_category": categorized,
            "failed_symbols": sorted(self._failed_symbols),
            "successful_symbols": sorted(self.successes.keys())
        }

        with open(self.LOG_PATH, "w") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        return self.LOG_PATH

    def print_summary(self):
        """Prints a colorful summary to the terminal."""
        print(f"\n{'=' * 60}")
        print(f"  📊 Bulk Fetch Summary")
        print(f"{'=' * 60}")
        print(f"  ✅ Success: {len(self.successes)} symbols "
              f"({sum(self.successes.values())} bars total)")
        print(f"  ❌ Failed:  {len(self._failed_symbols)} symbols")

        if self.errors:
            print(f"\n  Error Breakdown:")
            for cat, symbols in sorted(self.errors.items()):
                emoji = {
                    "QUALIFY_FAILED": "🔍",
                    "NO_DATA": "📭",
                    "NO_PERMISSIONS": "🔒",
                    "TIMEOUT": "⏱️",
                    "PACING": "🐌",
                    "CANCELLED": "🚫",
                    "UNKNOWN": "❓"
                }.get(cat, "❓")
                sym_list = sorted(symbols.keys())
                print(f"    {emoji} {cat}: {', '.join(sym_list)}")

        print(f"{'=' * 60}")


def get_ticker_currency(ticker: str, trades_dir: str = "./data/trades") -> tuple:
    """
    Reads the first TradeObject JSON for a ticker and returns (currency, exchange).
    Falls back to ('USD', '') if no trades or fields are absent.
    """
    ticker_dir = os.path.join(trades_dir, ticker)
    if not os.path.exists(ticker_dir):
        return ("USD", "")
    
    for fname in os.listdir(ticker_dir):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(ticker_dir, fname), "r") as f:
                data = json.load(f)
            return (data.get("currency", "USD"), data.get("exchange", ""))
        except (json.JSONDecodeError, OSError):
            continue
    
    return ("USD", "")


async def main_async(ticker_args: List[str], client_id: int, port: int):
    print(f"📉 Async Bulk Fetch (ID: {client_id}, Port: {port})...")
    
    # --- Setup Logger ---
    log = BulkFetchLogger()
    
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
            sym = t.split(':')[0].upper()
            if sym not in SKIP_TICKERS:
                symbols.append(sym)
    else:
        symbols = get_all_tickers()

    # --- Load Ticker Map + TradeObject Currency ---
    ticker_map = TickerMap()
    mapped = ticker_map.get_mapped()
    if mapped:
        print(f"  🗺️  Ticker mappings active: {', '.join(f'{k}→{v}' for k, v in mapped.items())}")
    unmapped = ticker_map.get_unmapped_count()
    if unmapped:
        print(f"  ⚠️  {unmapped} unmapped ticker(s) in ticker_map.json (will be skipped)")

    # Pre-scan TradeObject currencies for all symbols
    ticker_currencies = {}
    for s in symbols:
        curr, exch = get_ticker_currency(s)
        if curr != "USD" or exch:
            ticker_currencies[s] = (curr, exch)
    if ticker_currencies:
        non_usd = [f"{k}({v[0]})" for k, v in ticker_currencies.items()]
        print(f"  💱 Non-USD tickers from trades: {', '.join(non_usd)}")

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
    
    try:
        # Iterate years descending
        for year in range(current_year, start_year - 1, -1):
            processed_batch += 1
            end_date = f"{year}1231 23:59:59" 
            print(f"\n📅 Batch {processed_batch}/{total_batches}: Year {year}")
            
            # Create Requests for this year (Filter by Coverage + Ticker Map)
            reqs = []
            skipped = 0
            skipped_unmapped = 0
            for s in symbols:
                # If we already have this year fully covered, and it's not the current year (always update current)
                if year in coverage_map[s] and year != current_year:
                    skipped += 1
                    continue
                
                # Priority chain: ticker_map override > TradeObject currency > default USD
                override = ticker_map.resolve(s)
                
                if override == "SKIP":
                    # null mapping = skip (user hasn't mapped it yet)
                    skipped_unmapped += 1
                    continue
                
                if override is not None:
                    # Explicit mapping from ticker_map.json
                    ibkr_symbol, currency, exchange = override
                    reqs.append(HistoryRequest(
                        ibkr_symbol, '1 Y', end_date=end_date,
                        save_as=s if ibkr_symbol != s else '',
                        currency=currency, exchange=exchange
                    ))
                else:
                    # No override -> use TradeObject currency or default
                    currency, exchange = ticker_currencies.get(s, ("USD", ""))
                    reqs.append(HistoryRequest(
                        s, '1 Y', end_date=end_date,
                        currency=currency, exchange=exchange or "SMART"
                    ))
                
            if not reqs:
                skip_msg = f"All {skipped} covered"
                if skipped_unmapped:
                    skip_msg += f", {skipped_unmapped} unmapped"
                print(f"   -> Skipped ({skip_msg}).")
                continue
                
            skip_info = f"{skipped} covered"
            if skipped_unmapped:
                skip_info += f", {skipped_unmapped} unmapped"
            print(f"   -> Fetching {len(reqs)} symbols ({skip_info})...")
            
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
                         log.record_error(r.symbol, r.error_category or "UNKNOWN",
                                          r.error_message or "", year)
                         # Auto-register qualify failures in ticker_map
                         if r.error_category == "QUALIFY_FAILED":
                             ticker_map.register_failed(r.symbol)
            
            # Record successes
            for r in results:
                if r.success:
                    log.record_success(r.symbol, r.data_points_count)

            # Live-update log after each batch
            log.write()

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\n⚠️  Interrupted! Saving partial log...")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
    finally:
        # --- ALWAYS Write Log File ---
        log_path = log.write()
        
        print(f"\n✅ {'Partial' if processed_batch < total_batches else 'Full'} run complete.")
        print(f"📝 Log written to: {log_path}")
        log.print_summary()
        
        try:
            ib.disconnect()
        except Exception:
            pass

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", type=int, default=999, help="Reader Client ID")
    parser.add_argument("--port", type=int, default=4002, help="Gateway Port")
    parser.add_argument("tickers", nargs="*", help="List of tickers.")
    args = parser.parse_args()
        
    asyncio.run(main_async(args.tickers, args.client_id, args.port))

if __name__ == "__main__":
    run()
