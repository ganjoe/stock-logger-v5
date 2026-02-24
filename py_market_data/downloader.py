# py_market_data/downloader.py
import asyncio
import os
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from ib_insync import IB, Stock, Contract
from .domain import HistoryRequest, BatchDownloadResult, BatchConfig
from py_tradeobject.interface import BarData


def classify_error(error_msg: str) -> str:
    """Classifies an IBKR error message into a category."""
    msg_lower = error_msg.lower()
    if "qualify" in msg_lower or "no security definition" in msg_lower:
        return "QUALIFY_FAILED"
    elif "no data" in msg_lower or "hmds" in msg_lower or "keine daten" in msg_lower or "ergab keine" in msg_lower:
        return "NO_DATA"
    elif "permission" in msg_lower or "not allowed" in msg_lower:
        return "NO_PERMISSIONS"
    elif "timeout" in msg_lower:
        return "TIMEOUT"
    elif "pacing" in msg_lower or "violation" in msg_lower:
        return "PACING"
    elif "cancelled" in msg_lower or "query cancelled" in msg_lower:
        return "CANCELLED"
    else:
        return "UNKNOWN"

class BulkDownloader:
    def __init__(self, ib_client: IB, max_concurrent: int = 20):
        self.ib = ib_client
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.pacing_delay = 0.1 # Default live pacing
        self.pacing_delay = 0.1 # Default live pacing
        self.base_path = "./data/market_cache" 

    def check_coverage(self, symbol: str) -> set:
        """
        Scans existing 1D.json to find fully covered years.
        Returns a set of years (int) that have significant data (>200 days).
        """
        file_path = os.path.join(self.base_path, symbol.upper(), "charts", "1D.json")
        if not os.path.exists(file_path):
            return set()
            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [BulkDownloader] Warning: Could not read coverage for {symbol}: {e}")
            return set()
            
        # Count entries per year
        year_counts = {}
        for entry in data:
            raw_t = entry.get('t', entry.get('date', ''))
            
            # Extract year robustly
            if isinstance(raw_t, (int, float)):
                y = datetime.fromtimestamp(raw_t).year
            elif isinstance(raw_t, str) and len(raw_t) >= 4:
                try:
                    y = int(raw_t[:4])
                except ValueError:
                    continue
            else:
                continue
                
            year_counts[y] = year_counts.get(y, 0) + 1
                
        # Threshold: 200 trading days implies full year
        # (Trading years have ~252 days)
        covered_years = {y for y, count in year_counts.items() if count > 200}
        
        # Always exclude current year from "Coverage" to force update
        current_year = datetime.now().year
        if current_year in covered_years:
            covered_years.remove(current_year)
            
        return covered_years 

    async def verify_market_data_type(self) -> BatchConfig:
        """Determines market data permissions (Live vs Delayed) via robust smoke test."""
        print("🕵️ Detecting Market Data Permissions...")
        
        # Test Contract (SPY is liquid and standard)
        contract = Stock('SPY', 'SMART', 'USD')
        await self.ib.qualifyContractsAsync(contract)
        
        # Test 1: Live (1)
        try:
            self.ib.reqMarketDataType(1)
            bars = await self.ib.reqHistoricalDataAsync(
                contract, endDateTime='', durationStr='1 D', barSizeSetting='1 day',
                whatToShow='TRADES', useRTH=True, formatDate=1
            )
            if bars:
                print("✅ Live Data Confirmed. Using: Paid (Live)")
                return BatchConfig(1, 20, '30 Y', 0.1, "Paid Subscription (Live)") 
        except Exception as e:
            # Fallback to delayed check
            pass 

        # Test 2: Delayed (3)
        print("🔄 Switching to Delayed Data check...")
        try:
            self.ib.reqMarketDataType(3)
            bars = await self.ib.reqHistoricalDataAsync(
                contract, endDateTime='', durationStr='1 D', barSizeSetting='1 day',
                whatToShow='TRADES', useRTH=True, formatDate=1
            )
            if bars:
                print("✅ Delayed Data Confirmed. Using: Free (Delayed)")
                return BatchConfig(3, 1, '1 Y', 3.0, "Free Subscription (Delayed / Strict Pacing)") # 3.0s pacing as user suggested
        except Exception as e:
            print(f"❌ Market Data Permission Check Failed (Symbol: SPY): {e}")
            if "pacing" in str(e).lower() or "162" in str(e):
                print("💡 Hint: Possible IBKR Pacing Violation. Wait a few seconds and try again.")

        # Fallback
        return BatchConfig(4, 1, '1 Y', 5.0, "Frozen/Unknown (Fallback)")

    def _save_bars_merged(self, symbol: str, bars: List[Any]) -> int:
        """Merge logic: Loads existing data and appends new non-duplicate entries."""
        from .storage import load_bars, save_bars
        file_path = os.path.join(self.base_path, symbol.upper(), "charts", "1D.json")
        
        # 1. Load Existing (as our BarData objects)
        existing_bars = load_bars(file_path)

        # 2. Convert incoming IB bars to our BarData format
        new_bars = []
        for b in bars:
            # IB bar.date can be date or datetime
            dt = b.date if isinstance(b.date, datetime) else datetime.combine(b.date, datetime.min.time())
            new_bars.append(BarData(
                timestamp=dt,
                open=float(b.open),
                high=float(b.high),
                low=float(b.low),
                close=float(b.close),
                volume=float(b.volume)
            ))

        # 3. Save Combined
        # storage.save_bars handles deduplication (last wins) and sorting
        combined = existing_bars + new_bars
        save_bars(file_path, combined, timeframe="1D")
        
        # Note: new_count is tricky now because dedupe happens in save_bars.
        # But for reporting, seeing the incoming count is usually what's expected.
        return len(new_bars)

    async def run_batch(self, requests: List[HistoryRequest]) -> List[BatchDownloadResult]:
        """Starts batch download with pre-qualification."""
        if not requests: return []

        # 1. Qualify All Contracts Batch
        print(f"  🔍 Qualifying {len(requests)} contracts...")
        contracts = {}
        batch_stocks = []
        for req in requests:
            s = Stock(req.symbol, req.exchange, req.currency)
            key = f"{req.symbol}:{req.currency}:{req.exchange}"
            contracts[key] = s
            batch_stocks.append(s)
            
        try:
            await self.ib.qualifyContractsAsync(*batch_stocks)
        except Exception as e:
            print(f"  ⚠️ Qualify Warning: {e}")

        # 2. Execute Parallel
        tasks = []
        for req in requests:
            key = f"{req.symbol}:{req.currency}:{req.exchange}"
            c = contracts[key]
            if c.conId == 0:
                # Mock result for failure – report under original ticker name
                original = req.save_as or req.symbol
                async def fail_task(sym): return BatchDownloadResult(
                    sym, False, 0, "Qualify Failed", "QUALIFY_FAILED")
                tasks.append(fail_task(original))
            else:
                tasks.append(self._download_single(req, c))
                
        results = await asyncio.gather(*tasks)
        return list(results)

    async def _download_single(self, req: HistoryRequest, contract: Contract) -> BatchDownloadResult:
        """Downloads single ticker with semaphore and strict finally-pacing."""
        # Use save_as (original ticker) for reporting and storage, symbol for IBKR API
        report_symbol = req.save_as or req.symbol
        async with self.semaphore:
            try:
                bars = await self.ib.reqHistoricalDataAsync(
                    contract,
                    endDateTime=req.end_date,
                    durationStr=req.duration,
                    barSizeSetting=req.bar_size,
                    whatToShow=req.what_to_show,
                    useRTH=req.use_rth,
                    formatDate=1
                )
                
                if not bars:
                    return BatchDownloadResult(report_symbol, False, 0, "No Data Returned", "NO_DATA")

                # Map and Save – use original ticker name for storage
                count = self._save_bars_merged(report_symbol, bars)
                return BatchDownloadResult(report_symbol, True, count)

            except Exception as e:
                err_msg = str(e)
                return BatchDownloadResult(report_symbol, False, 0, err_msg, classify_error(err_msg))
            
            finally:
                # Enforce Pacing (Crucial for Free Data stability)
                await asyncio.sleep(self.pacing_delay)
