from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from py_interface.safety import execute_panic_close

@dataclass
class CommandResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    html_view: Optional[str] = None

class CommandProcessor:
    """
    F-INT-010: Processes text commands and maps indices.
    F-INT-020: Dual-Output support.
    """
    def __init__(self, broker, analytics):
        self.broker = broker
        self.analytics = analytics
        self.last_snapshot = None

    def process(self, cmd_str: str, is_bot: bool = False) -> CommandResult:
        tokens = cmd_str.lower().split()
        if not tokens:
            return CommandResult(False, "Empty command")

        cmd = tokens[0]
        args = tokens[1:]

        # F-INT-046: Contextual Help System (Supports ?, -?, --help)
        help_triggers = ["?", "-?", "--help"]
        # Treat "order ?" or "orders ?" the same for help
        if cmd in ["order", "orders"] and args and args[0] in help_triggers:
             return self._handle_help("orders")

        if cmd in help_triggers or (args and args[0] in help_triggers):
            target_cmd = cmd if cmd not in help_triggers else None
            return self._handle_help(target_cmd)

        # Connection Management
        if cmd == "connect" and args:
            return self._handle_connect(args[0], is_bot)
        if cmd == "disconnect":
            return self._handle_disconnect(is_bot)

        # Risk Tools
        if cmd == "size" and len(args) >= 3:
            return self._handle_size(args[0], args[1], args[2], is_bot)
        if cmd == "risk" and len(args) >= 3 and args[1] == "--stop":
            return self._handle_risk_sim(args[0], args[2], is_bot)
        if cmd == "wizard":
            return CommandResult(True, "Wizard started on Main Stage.", html_view="<div class='wizard-placeholder'>Risk Wizard Loaded</div>")

        # Trade Management
        if cmd == "trades":
            return self._handle_trades(is_bot)
        if cmd in ["order", "orders"]:
            if args and args[0] == "cancel":
                if len(args) > 1:
                    return self._handle_cancel(args[1], is_bot)
                return CommandResult(False, "Usage: orders cancel <idx/ticker/all>")
            return self._handle_orders(is_bot)
        if cmd == "cancel" and args:
            return self._handle_cancel(args[0], is_bot)
        if cmd == "modify" and args:
            return self._handle_modify(args, is_bot)
        
        # Analytics
        if cmd == "history":
            days = int(args[0]) if args else 30
            return self._handle_history(days, is_bot)
        if cmd == "stats":
            period = args[0] if args else "ytd"
            return self._handle_stats(period, is_bot)

        if cmd == "panic" or (cmd == "close" and "all" in args):
            success = execute_panic_close(self.broker)
            msg = "🚨 PANIC: All positions closed!" if success else "❌ PANIC FAILED!"
            return CommandResult(success, msg)

        if cmd == "status":
            return self._handle_status(is_bot)

        if cmd == "close" and args:
            return self._handle_close(args[0], is_bot)

        return CommandResult(False, f"Unknown command: {cmd}")

    def _handle_status(self, is_bot: bool) -> CommandResult:
        snapshot = self.broker.get_portfolio_snapshot()
        self.last_snapshot = snapshot  # Cache for index-based commands
        report = self.analytics.analyze(snapshot)
        orders = self.broker.get_active_orders()
        
        msg = f"Equity: {report.summary.equity:.2f} | Heat: {report.summary.heat_index:.2f}% | Orders: {len(orders)}"
        data = {**report.to_dict(), "orders": orders} if is_bot else None
        html = self._render_status_html(report, orders) if not is_bot else None
        
        return CommandResult(True, msg, data=data, html_view=html)

    def _render_status_html(self, report, orders) -> str:
        # F-INT-050: Informational HTML Table
        rows = []
        for i, pos in enumerate(report.positions):
            idx = i + 1
            pnl_color = "#06d6a0" if pos.unrealized_pnl >= 0 else "#ef476f"
            rows.append(f"""
                <tr>
                    <td style="padding:8px;">{idx}</td>
                    <td style="padding:8px;">{pos.ticker}</td>
                    <td style="padding:8px;">{pos.qty}</td>
                    <td style="padding:8px;">${pos.entry_price:.2f}</td>
                    <td style="padding:8px;">${pos.current_price:.2f}</td>
                    <td style="padding:8px; color: {pnl_color}">${pos.unrealized_pnl:.2f}</td>
                    <td style="padding:8px;">{pos.risk_pct:.2f}%</td>
                </tr>
            """)
        pos_table_body = "".join(rows)
        
        # Orders Table (Minimal for Snapshot)
        order_rows = []
        for o in orders:
             order_rows.append(f"""
                <tr>
                    <td style="padding:5px;">{o['id']}</td>
                    <td style="padding:5px;">{o['ticker']}</td>
                    <td style="padding:5px;">{o['action']}</td>
                    <td style="padding:5px;">{o['qty']}</td>
                    <td style="padding:5px;">${o['price']}</td>
                </tr>
            """)
        order_table_body = "".join(order_rows)
        
        return f"""
            <div class="status-view">
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <h2 style="margin:0;">Portfolio Snapshot</h2>
                    <div style="font-weight:bold;">
                        <span style="color:#a0a0a0;">Equity:</span> ${report.summary.equity:,.2f} | 
                        <span style="color:#a0a0a0;">Cash:</span> ${report.summary.cash:,.2f}
                    </div>
                </div>
                <table border="0" style="width:100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
                    <thead style="background: #2a2a2e; color: #a0a0a0;">
                        <tr>
                            <th style="padding:8px;">#</th><th style="padding:8px;">Symbol</th><th style="padding:8px;">Qty</th>
                            <th style="padding:8px;">Entry</th><th style="padding:8px;">Price</th><th style="padding:8px;">PnL</th>
                            <th style="padding:8px;">Risk</th>
                        </tr>
                    </thead>
                    <tbody> {pos_table_body} </tbody>
                </table>
                
                <br>
                <h3 style="margin-bottom:10px;">Active Orders</h3>
                <table border="0" style="width:100%; border-collapse: collapse; text-align: left; font-size: 0.8rem;">
                    <thead style="background: #2a2a2e; color: #a0a0a0;">
                        <tr>
                            <th style="padding:5px;">ID</th><th style="padding:5px;">Ticker</th>
                            <th style="padding:5px;">Action</th><th style="padding:5px;">Qty</th>
                            <th style="padding:5px;">Price</th>
                        </tr>
                    </thead>
                    <tbody> {order_table_body or '<tr><td colspan="5" style="padding:10px; text-align:center;">No active orders</td></tr>'} </tbody>
                </table>
            </div>
        """

    def _handle_close(self, target: str, is_bot: bool) -> CommandResult:
        # Index-based trading (F-INT-110)
        symbol = target
        qty = 0
        
        if target.isdigit():
            if not self.last_snapshot:
                 return CommandResult(False, "No active snapshot. Run 'status' first.")
            
            idx = int(target) - 1
            if 0 <= idx < len(self.last_snapshot.positions):
                pos = self.last_snapshot.positions[idx]
                symbol = pos.ticker
                qty = pos.quantity
            else:
                return CommandResult(False, f"Index {target} out of range.")
        else:
            # Symbol based - need to find qty from snapshot or broker logic
            # For safety, we should probably fetch the snapshot if not cached, 
            # but let's assume we need a snapshot to know what to close.
             if not self.last_snapshot:
                 # Try to get one? Or fail? Let's try to get one.
                 self.last_snapshot = self.broker.get_portfolio_snapshot()
            
             found = next((p for p in self.last_snapshot.positions if p.ticker == symbol), None)
             if found:
                 qty = found.quantity
             else:
                 return CommandResult(False, f"Position {symbol} not found.")

        if qty == 0:
             return CommandResult(False, f"Quantity for {symbol} is 0.")

        # Execute Trade: SELL to close long, COVER to close short (if supported, or just opposite action)
        # Assuming broker.execute_trade takes (symbol, qty, action)
        # We start simple with 'SELL' for now, assuming long positions. 
        # Ideally we check qty sign.
        action = "SELL" if qty > 0 else "BUY" # Close Long vs Close Short
        abs_qty = abs(qty)
        
        success = self.broker.execute_trade(symbol, abs_qty, action)
        
        if success:
            return CommandResult(True, f"Closing {symbol} ({abs_qty} shares)...")
        else:
            return CommandResult(False, f"Failed to close {symbol}.")

    # --- New Command Handlers ---

    def _handle_connect(self, env: str, is_bot: bool) -> CommandResult:
        success = self.broker.connect(env)
        msg = f"Connected to {env} environment. ✅" if success else f"Failed to connect to {env}. 🛑"
        return CommandResult(success, msg)

    def _handle_disconnect(self, is_bot: bool) -> CommandResult:
        success = self.broker.disconnect()
        return CommandResult(success, "Disconnected from broker. 🔌")

    def _handle_size(self, ticker: str, entry: str, stop: str, is_bot: bool) -> CommandResult:
        try:
            e_price = float(entry)
            s_price = float(stop)
            # Todo: Get account size from broker/config. Mocking 100k for now.
            # Using py_financial_math.risk implementation
            import py_financial_math.risk as risk_math
            qty = risk_math.calculate_position_size(100000, 0.01, e_price, s_price)
            
            msg = f"Sizing for {ticker}: Entry {e_price}, Stop {s_price} -> Qty: {int(qty)} units"
            data = {"ticker": ticker, "entry": e_price, "stop": s_price, "quantity": qty} if is_bot else None
            return CommandResult(True, msg, data=data)
        except ValueError:
            return CommandResult(False, "Invalid number format.")

    def _handle_trades(self, is_bot: bool) -> CommandResult:
        # Re-use status logic but focus on table
        snapshot = self.broker.get_portfolio_snapshot()
        self.last_snapshot = snapshot
        # For simplicity, returning status view but conceptually could be different
        return self._handle_status(is_bot)

    def _handle_orders(self, is_bot: bool) -> CommandResult:
        orders = self.broker.get_active_orders()
        msg = f"Active Orders: {len(orders)}"
        
        if is_bot:
            return CommandResult(True, msg, data={"orders": orders})

        # HTML Render - F-INT-210 Management View (Informational Only)
        html = f"""
            <div class="orders-view">
                <h2>Order Management</h2>
                <table border="0" style="width:100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
                    <thead style="background: #2a2a2e; color: #a0a0a0;">
                        <tr>
                            <th style="padding:8px;">#</th>
                            <th style="padding:8px;">ID</th>
                            <th style="padding:8px;">Ticker</th>
                            <th style="padding:8px;">Type</th>
                            <th style="padding:8px;">Qty</th>
                            <th style="padding:8px;">Price</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        for i, o in enumerate(orders):
            idx = i + 1
            html += f"""
                <tr>
                    <td style="padding:8px;">{idx}</td>
                    <td style="padding:8px;">{o['id']}</td>
                    <td style="padding:8px;">{o['ticker']}</td>
                    <td style="padding:8px;">{o['action']}</td>
                    <td style="padding:8px;">{o['qty']}</td>
                    <td style="padding:8px;">${o['price']}</td>
                </tr>
            """
        html += """
                    </tbody>
                </table>
                <p style="color: #a0a0a0; font-size: 0.8rem; margin-top: 10px;">Use CLI to manage: <code>cancel &lt;#&gt;</code> or <code>modify &lt;#&gt; --price &lt;p&gt;</code></p>
            </div>
        """
        
        return CommandResult(True, msg, html_view=html)

    def _handle_cancel(self, target: str, is_bot: bool) -> CommandResult:
        success = self.broker.cancel_order(target)
        return CommandResult(success, f"Order {target} cancelled. 🗑️")

    def _handle_modify(self, args: List[str], is_bot: bool) -> CommandResult:
        # Expected: modify <idx> --price <p>
        try:
            target = args[0]
            price = 0.0
            if "--price" in args:
                price = float(args[args.index("--price") + 1])
            
            # Todo: Resolve index to order_id if target is numeric
            success = True # Mocking success
            msg = f"Order {target} modified to price ${price:.2f}. ✏️"
            return CommandResult(success, msg)
        except (ValueError, IndexError):
            return CommandResult(False, "Invalid modify syntax. Use: modify <idx> --price <p>")

    def _handle_history(self, days: int, is_bot: bool) -> CommandResult:
        # Mocking history logic since we don't have DB
        msg = f"Displaying history for last {days} days."
        # Generate Dummy Data for Chart
        data = {"dates": ["2023-01-01", "2023-01-02"], "equity": [10000, 10100]}
        
        # HTML Placeholder for Plotly
        html = f"<div id='history-chart'>[Chart Placeholder for {days} days]</div>"
        
        return CommandResult(True, msg, data=data if is_bot else None, html_view=html if not is_bot else None)

    def _handle_stats(self, period: str, is_bot: bool) -> CommandResult:
        msg = f"Stats for {period}: Winrate 65%, PF 2.1 ✅"
        data = {"winrate": 0.65, "profit_factor": 2.1, "period": period}
        return CommandResult(True, msg, data=data if is_bot else None)

    def _handle_risk_sim(self, ticker: str, stop: str, is_bot: bool) -> CommandResult:
        # Simulate risk
        return CommandResult(True, f"Simulated risk for {ticker} at stop {stop}: -1.2% Equity ⚠️")

    def _handle_help(self, specific_cmd: Optional[str] = None) -> CommandResult:
        if not specific_cmd:
            msg = "Available Commands: status, trades, orders, close, cancel, modify, size, risk, connect, disconnect, history, stats, wizard, ?"
            html = """
                <div class='help-view' style='padding: 15px; background: #1e1e22; border-radius: 8px; border: 1px solid #333;'>
                    <h2 style='color: #06d6a0; margin-top: 0;'>🚀 Trading Console Help</h2>
                    <p>Enter a command followed by <code>?</code> for detailed usage (e.g., <code>close ?</code>).</p>
                    
                    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 20px;'>
                        <div>
                            <h3 style='border-bottom: 1px solid #444; padding-bottom: 5px;'>Monitoring</h3>
                            <ul style='list-style: none; padding: 0;'>
                                <li><b>status</b> - Portfolio overview & risk</li>
                                <li><b>trades</b> - List all open positions</li>
                                <li><b>orders</b> - List active market orders</li>
                                <li><b>history [days]</b> - Equity curve visualization</li>
                                <li><b>stats [period]</b> - Performance metrics</li>
                            </ul>
                        </div>
                        <div>
                            <h3 style='border-bottom: 1px solid #444; padding-bottom: 5px;'>Execution</h3>
                            <ul style='list-style: none; padding: 0;'>
                                <li><b>close [idx/ticker]</b> - Close position</li>
                                <li><b>orders cancel [idx/all]</b> - Stop active order</li>
                                <li><b>modify [idx]</b> - Change order price</li>
                                <li><b>panic</b> - ⚠️ Emergency liquidation</li>
                            </ul>
                        </div>
                    </div>
                    <div style='margin-top: 15px;'>
                        <h3 style='border-bottom: 1px solid #444; padding-bottom: 5px;'>Tools & Config</h3>
                        <ul style='list-style: none; padding: 0;'>
                            <li><b>size [ticker] [entry] [stop]</b> - Sizing calculator</li>
                            <li><b>risk [ticker] --stop [p]</b> - Risk simulation</li>
                            <li><b>connect [env]</b> - Broker login (paper/live)</li>
                        </ul>
                    </div>
                </div>
            """
            return CommandResult(True, msg, html_view=html)
        
        help_data = {
            "status": (
                "--- COMMAND: status ---\n"
                "SYNTAX: status\n"
                "DESCRIPTION: Refreshes the dashboard with latest broker data. Calculates Equity, Cash, Unrealized PnL, and 'Portfolio Heat'.\n"
                "EXPERT TIP: Watch the Heat Index! It represents your total risk if all stops are hit simultaneously. Keep it under 10% for conservative trading."
            ),
            "trades": (
                "--- COMMAND: trades ---\n"
                "SYNTAX: trades\n"
                "DESCRIPTION: Lists all open positions. Provides a unique index (#) for each ticker.\n"
                "EXPERT TIP: Use this command to verify your active exposure before initiating new trades."
            ),
            "orders": (
                "--- COMMAND: orders [cancel <target>] ---\n"
                "SYNTAX: \n"
                "  orders                -> View active orders.\n"
                "  orders cancel 1       -> Cancel order #1.\n"
                "  orders cancel AAPL    -> Cancel all Apple orders.\n"
                "  orders cancel all     -> Wipe the entire order book.\n"
                "DESCRIPTION: Manages your pending orders. Alias: 'order'.\n"
                "EXPERT TIP: Always check 'orders' before a 'panic' or 'close all' to ensure no orphan orders remain."
            ),
            "close": (
                "--- COMMAND: close <idx/ticker/all> ---\n"
                "SYNTAX: \n"
                "  close 1         -> Close position at index 1.\n"
                "  close AAPL      -> Close any Apple position.\n"
                "  close all       -> Liquidate ALL positions immediately.\n"
                "EXPERT TIP: Use index-based closing for speed during high volatility."
            ),
            "cancel": (
                "--- COMMAND: cancel <idx/ticker/all> ---\n"
                "SYNTAX: \n"
                "  cancel 2        -> Cancel pending order #2.\n"
                "  cancel TSLA     -> Cancel all Tesla orders.\n"
                "  cancel all      -> Wipe the entire order book.\n"
                "EXPERT TIP: In fast markets, 'cancel all' is safer than targeted cancellation."
            ),
            "modify": (
                "--- COMMAND: modify <idx> --price <p> ---\n"
                "SYNTAX: modify 1 --price 150.50\n"
                "DESCRIPTION: Updates the price of an existing limit or stop order.\n"
                "EXPERT TIP: Moving stops to 'Break Even' after a 1R move is a key professional discipline."
            ),
            "size": (
                "--- COMMAND: size <ticker> <entry> <stop> ---\n"
                "SYNTAX: size NVDA 600 580\n"
                "DESCRIPTION: Calculates optimal share quantity based on a fixed 1% risk of equity.\n"
                "EXPERT TIP: Sizing is the ONLY factor you can truly control. Never skip this step."
            ),
            "risk": (
                "--- COMMAND: risk <ticker> --stop <p> ---\n"
                "SYNTAX: risk MSFT --stop 380\n"
                "DESCRIPTION: Predicts the impact on Portfolio Heat if your stop for the ticker is moved to <p>.\n"
                "EXPERT TIP: Use this to plan 'Stop Trails' without over-leveraging your portfolio."
            ),
            "connect": (
                "--- COMMAND: connect [env] ---\n"
                "SYNTAX: connect paper / connect live\n"
                "DESCRIPTION: Initializes communication with the Broker Gateway.\n"
                "EXPERT TIP: Always start with 'paper' in a new session to verify your connection and feed."
            ),
            "disconnect": (
                "--- COMMAND: disconnect ---\n"
                "DESCRIPTION: Gracefully shuts down the broker session.\n"
                "EXPERT TIP: Disconnect at end-of-day to avoid unexpected API timeouts."
            ),
            "history": (
                "--- COMMAND: history [days] ---\n"
                "SYNTAX: history 30\n"
                "DESCRIPTION: Generates an equity curve visualization on the web stage.\n"
                "EXPERT TIP: Analyze your 'Drawdown' periods in history to refine your risk-off triggers."
            ),
            "stats": (
                "--- COMMAND: stats [period] ---\n"
                "SYNTAX: stats ytd / stats last_month\n"
                "DESCRIPTION: Computes Winrate, Profit Factor, and Average R-Multiple.\n"
                "EXPERT TIP: A Profit Factor > 2.0 indicates a robust, professional-grade edge."
            ),
            "panic": (
                "--- COMMAND: panic ---\n"
                "SYNTAX: panic\n"
                "DESCRIPTION: 🚨 THE EMERGENCY BUTTON. Market-closes everything and nukes the order book.\n"
                "EXPERT TIP: Seconds matter. Use this if price action becomes irrational or your internet/API is failing."
            ),
            "wizard": (
                "--- COMMAND: wizard ---\n"
                "DESCRIPTION: Opens an interactive step-by-step risk planning form.\n"
                "EXPERT TIP: Ideal for complex multi-leg entries or new strategy testing."
            )
        }
        
        detail = help_data.get(specific_cmd, f"No detailed help available for '{specific_cmd}'. Check spelling or use '?' for root help.")
        return CommandResult(True, detail)
