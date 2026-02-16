# py_market_data/downloader.py
import asyncio
from typing import List, Dict
from datetime import datetime
from ib_insync import IB, Stock, Contract
from .domain import HistoryRequest, BatchDownloadResult, BatchConfig
from .storage import save_bars
from py_tradeobject.interface import BarData

class BulkDownloader:
    def __init__(self, ib_client: IB, max_concurrent: int = 20):
        self.ib = ib_client
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.pacing_delay = 0.1 # Default live pacing

    async def run_batch(self, requests: List[HistoryRequest]) -> List[BatchDownloadResult]:
        """Startet den Bulk-Download Prozess."""
        if not requests:
            return []

        # 1. Qualify Contracts Batch
        contracts: Dict[str, Contract] = {} 
        stock_list = []
        
        print(f"  🔍 Qualifying {len(requests)} contracts...")
        for req in requests:
            c = Stock(req.symbol, 'SMART', 'USD')
            contracts[req.symbol] = c
            stock_list.append(c)
            
        try:
            await self.ib.qualifyContractsAsync(*stock_list)
        except Exception as e:
            print(f"  ⚠️ Warning: Bulk qualification partial failure: {e}")

        # 2. Parallel Execution
        tasks = []
        for req in requests:
            contract = contracts[req.symbol]
            tasks.append(self._download_single(req, contract))
            
        results = await asyncio.gather(*tasks)
        return list(results)

    async def _download_single(self, req: HistoryRequest, contract: Contract) -> BatchDownloadResult:
        """Lädt einen einzelnen Ticker unter Beachtung der Semaphore und Retry-Logik."""
        
        if contract.conId == 0:
             return BatchDownloadResult(req.symbol, False, 0, "Qualify Failed (Unknown Symbol)")

        async with self.semaphore:
            RETRIES = 3
            for attempt in range(RETRIES):
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

                    mapped_bars = []
                    for b in bars:
                        ts = b.date
                        if not isinstance(ts, datetime):
                             try:
                                 ts = datetime(ts.year, ts.month, ts.day)
                             except:
                                 pass 
                        
                        mapped_bars.append(BarData(
                            timestamp=ts,
                            open=float(b.open), 
                            high=float(b.high), 
                            low=float(b.low), 
                            close=float(b.close), 
                            volume=float(b.volume)
                        ))

                    save_bars(f"./data/market_cache/{req.symbol}/charts/{self._map_bar_size(req.bar_size)}.json", mapped_bars)
                    
                    # Success -> Break loop
                    return BatchDownloadResult(req.symbol, True, len(mapped_bars))

                except Exception as e:
                    msg = str(e)
                    # Check for Pacing Violation
                    # Error 162: Historical Market Data Service error message:HMDS query returned no data: ...
                    # OR: "API historical data query cancelled" (which happens on timeout/limit)
                    
                    if attempt < RETRIES - 1:
                        wait_time = 10 * (attempt + 1) # Linear backoff: 10s, 20s, 30s
                        print(f"    ⚠️ Retry {req.symbol} ({attempt+1}/{RETRIES}) after {wait_time}s due to error: {msg}")
                        # Pacing Breath (We need to pass delay somehow, or move delay to downloader init)
                        # But downloader was initialized before config was known in bulk_fetch...
                        # Wait, bulk_fetch re-assigns semaphore but not delay.
                        # Let's just fix downloader init to allow updating delay.
                        await asyncio.sleep(self.pacing_delay) # Apply pacing delay before retry
                        await asyncio.sleep(wait_time) # Apply backoff delay
                    else:
                        return BatchDownloadResult(req.symbol, False, 0, f"Failed after {RETRIES} retries. Last error: {msg}")

            return BatchDownloadResult(req.symbol, False, 0, "Unknown Error Loop")
    
    def _map_bar_size(self, bar_size: str) -> str:
        if "day" in bar_size: return "1D"
        if "min" in bar_size: return "1min" 
        return "1D" # Default

    async def verify_market_data_type(self) -> BatchConfig:
        """Determines market data permissions (Live vs Delayed) and returns config."""
        print("🕵️ Detecting Market Data Permissions...")
        
        # Test Contract (SPY is liquid and standard)
        contract = Stock('SPY', 'SMART', 'USD')
        await self.ib.qualifyContractsAsync(contract)
        
        # Default: Paid / Live
        config = BatchConfig(
            market_data_type=1, # Real-time
            max_concurrent=20, # User specified 20-50 limit
            default_duration='30 Y',
            pacing_delay=0.1,
            description="Paid Subscription (Live)"
        )

        try:
            # Switch to Live (1) to test
            self.ib.reqMarketDataType(1)
            bars = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime='',
                durationStr='1 D', # Short test
                barSizeSetting='1 day',
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            if not bars:
                raise Exception("No data returned for SPY (Live)")
                
            print(f"✅ Live Data Confirmed. Using: {config.description}")
            return config

        except Exception as e:
            # Fallback to Delayed (3)
            print(f"⚠️ Live Data Check Failed: {e}")
            print(f"🔄 Switching to Delayed Data (Type 3)...")
            
            self.ib.reqMarketDataType(3) # Delayed
            
            # Re-test with Delayed
            try:
                bars = await self.ib.reqHistoricalDataAsync(
                    contract, 
                    endDateTime='', 
                    durationStr='1 D', 
                    barSizeSetting='1 day', 
                    whatToShow='TRADES', 
                    useRTH=True, 
                    formatDate=1
                )
                if bars:
                    print("✅ Delayed Data Confirmed.")
                    return BatchConfig(
                        market_data_type=3,
                        max_concurrent=1,         # Strict Serial
                        default_duration='1 Y',   # Free Limit per Request!
                        pacing_delay=10.0,        # 60 reqs / 10 min = 1 req / 10s strict
                        description="Free Subscription (Delayed / Strict Pacing)"
                    )
            except Exception as e2:
                print(f"❌ Delayed Data Check Also Failed: {e2}")
                
            # If all fails, return Frozen or just default with warning
            return BatchConfig(4, 1, '1 Y', 10.0, "Frozen/Unknown (Fallback)")
