# py_market_data/downloader.py
import asyncio
import os
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from ib_insync import IB, Stock, Contract
from .domain import HistoryRequest, BatchDownloadResult, BatchConfig
from py_tradeobject.interface import BarData

class BulkDownloader:
    def __init__(self, ib_client: IB, max_concurrent: int = 20):
        self.ib = ib_client
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.pacing_delay = 0.1 # Default live pacing
        self.base_path = "./data/market_cache" 

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
        except Exception:
            pass # Fail silently, try delayed

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
            print(f"❌ Market Data Check Failed: {e}")

        # Fallback
        return BatchConfig(4, 1, '1 Y', 5.0, "Frozen/Unknown (Fallback)")

    def _save_bars_merged(self, symbol: str, bars: List[Any]) -> int:
        """Merge logic: Loads existing data and appends new non-duplicate entries."""
        file_path = os.path.join(self.base_path, symbol.upper(), "charts", "1D.json")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        existing_data = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []

        # Standard Keys: t, o, h, l, c, v
        seen_timestamps = set()
        for entry in existing_data:
            if 't' in entry:
                seen_timestamps.add(entry['t'])
            elif 'date' in entry: # Legacy support
                 seen_timestamps.add(entry['date'])

        new_entries = []
        for bar in bars:
            # Parse Date/Timestamp
            ts_str = bar.date.isoformat() if hasattr(bar.date, 'isoformat') else str(bar.date)
            # Normalize timestamp to match storage format (t)
            # If storage uses '2023-01-01', we use that.
            
            if ts_str not in seen_timestamps:
                new_entries.append({
                    "t": ts_str,
                    "o": float(bar.open),
                    "h": float(bar.high),
                    "l": float(bar.low),
                    "c": float(bar.close),
                    "v": int(bar.volume)
                })

        if new_entries:
            combined = existing_data + new_entries
            # Sort by timestamp
            combined.sort(key=lambda x: x.get('t', x.get('date', '')))
            with open(file_path, 'w') as f:
                json.dump(combined, f, indent=2)
                
        return len(new_entries)

    async def run_batch(self, requests: List[HistoryRequest]) -> List[BatchDownloadResult]:
        """Starts batch download with pre-qualification."""
        if not requests: return []

        # 1. Qualify All Contracts Batch
        print(f"  🔍 Qualifying {len(requests)} contracts...")
        contracts = {}
        batch_stocks = []
        for req in requests:
            s = Stock(req.symbol, 'SMART', 'USD')
            contracts[req.symbol] = s
            batch_stocks.append(s)
            
        try:
            await self.ib.qualifyContractsAsync(*batch_stocks)
        except Exception as e:
            print(f"  ⚠️ Qualify Warning: {e}")

        # 2. Execute Parallel
        tasks = []
        for req in requests:
            c = contracts[req.symbol]
            if c.conId == 0:
                # Mock result for failure
                # Note: run_batch expects awaitable tasks
                async def fail_task(r): return BatchDownloadResult(r.symbol, False, 0, "Qualify Failed")
                tasks.append(fail_task(req))
            else:
                tasks.append(self._download_single(req, c))
                
        results = await asyncio.gather(*tasks)
        return list(results)

    async def _download_single(self, req: HistoryRequest, contract: Contract) -> BatchDownloadResult:
        """Downloads single ticker with semaphore and strict finally-pacing."""
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
                    return BatchDownloadResult(req.symbol, False, 0, "No Data Returned")

                # Map and Save
                count = self._save_bars_merged(req.symbol, bars)
                return BatchDownloadResult(req.symbol, True, count)

            except Exception as e:
                return BatchDownloadResult(req.symbol, False, 0, str(e))
            
            finally:
                # Enforce Pacing (Crucial for Free Data stability)
                await asyncio.sleep(self.pacing_delay)
