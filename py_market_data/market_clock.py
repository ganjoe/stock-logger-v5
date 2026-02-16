# py_market_data/market_clock.py
from datetime import datetime, time, timedelta, date
import pytz

class MarketClock:
    """
    Simples Modell für NYSE Handelszeiten inklusive Feiertage (2024-2026).
    """
    
    TIMEZONE = pytz.timezone('US/Eastern')
    OPEN_TIME = time(9, 30)
    CLOSE_TIME = time(16, 0)
    
    # NYSE Holidays (Hardcoded for Robustness 2024-2026)
    # Format: YYYY-MM-DD
    HOLIDAYS = {
        date(2024, 1, 1),   # New Year's Day
        date(2024, 1, 15),  # MLK Day
        date(2024, 2, 19),  # Washington's Birthday
        date(2024, 3, 29),  # Good Friday
        date(2024, 5, 27),  # Memorial Day
        date(2024, 6, 19),  # Juneteenth
        date(2024, 7, 4),   # Independence Day
        date(2024, 9, 2),   # Labor Day
        date(2024, 11, 28), # Thanksgiving Day
        date(2024, 12, 25), # Christmas Day
        
        date(2025, 1, 1),   # New Year's Day
        date(2025, 1, 20),  # MLK Day
        date(2025, 2, 17),  # Washington's Birthday
        date(2025, 4, 18),  # Good Friday
        date(2025, 5, 26),  # Memorial Day
        date(2025, 6, 19),  # Juneteenth
        date(2025, 7, 4),   # Independence Day
        date(2025, 9, 1),   # Labor Day
        date(2025, 11, 27), # Thanksgiving Day
        date(2025, 12, 25), # Christmas Day

        date(2026, 1, 1),   # New Year's Day
        date(2026, 1, 19),  # MLK Day
        date(2026, 2, 16),  # Washington's Birthday
        date(2026, 4, 3),   # Good Friday
        date(2026, 5, 25),  # Memorial Day
        date(2026, 6, 19),  # Juneteenth
        date(2026, 7, 3),   # Independence Day (Observed for Sat 4th)
        date(2026, 9, 7),   # Labor Day
        date(2026, 11, 26), # Thanksgiving Day
        date(2026, 12, 25), # Christmas Day
    }
    
    @staticmethod
    def get_status() -> dict:
        now = datetime.now(MarketClock.TIMEZONE)
        today_date = now.date()
        current_time = now.time()
        
        status = "CLOSED"
        next_event = "OPEN"
        time_to_event = timedelta(0)
        
        # 1. Holiday Check (Today)
        if today_date in MarketClock.HOLIDAYS:
            status = "CLOSED (HOLIDAY)"
            # Find next valid open day
            next_open = MarketClock._get_next_open(now)
            time_to_event = next_open - now
            
        # 2. Weekend Check
        elif today_date.weekday() >= 5: # 5=Sat, 6=Sun
            status = "CLOSED (WEEKEND)"
            next_open = MarketClock._get_next_open(now)
            time_to_event = next_open - now
            
        # 3. Weekday Logic
        else:
            if current_time < MarketClock.OPEN_TIME:
                status = "PRE-MARKET"
                # Time to Open today
                today_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
                time_to_event = today_open - now
                
            elif MarketClock.OPEN_TIME <= current_time < MarketClock.CLOSE_TIME:
                status = "OPEN"
                next_event = "CLOSE"
                # Time to Close today
                today_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
                # Early Close on some days? (Not implemented for simplicity, e.g. Black Friday exits at 1pm)
                time_to_event = today_close - now
                
            else:
                status = "POST-MARKET / CLOSED"
                # Time to Next Open (Tomorrow or Next Business Day)
                next_open = MarketClock._get_next_open(now)
                time_to_event = next_open - now

        # 0. Calendar Staleness Check
        max_holiday_year = 2026
        calendar_outdated = now.year > max_holiday_year
        if calendar_outdated:
             status += " (CALENDAR OUTDATED - UPDATE HOLIDAYS)"

        return {
            "status": status,
            "server_time_et": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "next_event": next_event,
            "seconds_to_next_event": int(time_to_event.total_seconds()),
            "human_readable": str(time_to_event).split('.')[0],
            "calendar_outdated": calendar_outdated
        }

    @staticmethod
    def _get_next_open(current_dt: datetime) -> datetime:
        """Findet den nächsten offenen Handelstag (9:30 AM ET)."""
        candidate = current_dt + timedelta(days=1)
        while True:
            # Weekend?
            if candidate.weekday() >= 5:
                candidate += timedelta(days=1)
                continue
            
            # Holiday?
            if candidate.date() in MarketClock.HOLIDAYS:
                candidate += timedelta(days=1)
                continue
                
            # Valid business day found
            return candidate.replace(hour=9, minute=30, second=0, microsecond=0)
