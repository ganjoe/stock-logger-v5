# py_cli/handlers_history.py
from typing import List
from datetime import datetime, timedelta
from .models import CLIContext, CommandResponse
from .commands import ICommand, registry
from py_portfolio_state.history import HistoryFactory
from py_market_data.manager import ChartManager
from py_captrader import services

class HistoryCommand(ICommand):
    name = "history"
    description = "Retrieves historical portfolio snapshot."
    syntax = "history [days_back] (default=0)"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        days_back = 0
        if args:
            try:
                days_back = int(args[0])
            except ValueError:
                return CommandResponse(False, "Invalid days_back argument. Must be integer.", error_code="INVALID_ARG")

        # 1. Setup Factory
        provider = None
        if services.has_broker():
            provider = services.get_broker()
            
        # ChartManager is now handled internally by TradeObject (via set_broker)
        factory = HistoryFactory(trades_dir="./data/trades", provider=provider)
        
        # 2. Load Trades
        factory.load_all_trades()
        
        # 3. Get Snapshot
        target_date = datetime.now() - timedelta(days=days_back)
        snapshot = factory.get_snapshot_at(target_date)
        
        return CommandResponse(
            True,
            message=f"History Snapshot at {target_date.strftime('%Y-%m-%d %H:%M:%S')}",
            payload=snapshot.to_dict()
        )

registry.register(HistoryCommand())
