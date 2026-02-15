document.getElementById('cmd-input').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        const cmd = this.value;
        this.value = '';
        processCommand(cmd);
    }
});

document.getElementById('panic-btn').addEventListener('click', function () {
    if (confirm("🚨 ARE YOU SURE? This will close ALL positions immediately!")) {
        processCommand('panic');
    }
});

// F-INT-047: Visual Routing & Auto-Start
window.onload = function () {
    processCommand('status');
};

function updateNav(cmd) {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (cmd.startsWith('status') && btn.innerText.includes('Snapshot')) btn.classList.add('active');
        if (cmd.startsWith('orders') && btn.innerText.includes('Orders')) btn.classList.add('active');
        if (cmd.startsWith('history') && btn.innerText.includes('Analytics')) btn.classList.add('active');
    });
}

function processCommand(cmd) {
    logToTerminal(`> ${cmd}`, 'cmd');
    updateNav(cmd);

    // Simulate API call to backend
    // In a real app, this would be: fetch('/api/command', { method: 'POST', body: JSON.stringify({cmd}) })

    setTimeout(() => {
        handleResponse({
            success: true,
            message: getMockMessage(cmd),
            html_view: getMockHtml(cmd),
            data: { equity: 52430.50, cash: 12000.00, heat: 1.45 }
        });
    }, 200);
}

function handleResponse(res) {
    logToTerminal(res.message);

    if (res.data) {
        document.getElementById('stat-equity').innerText = `Equity: $${res.data.equity.toFixed(2)}`;
        document.getElementById('stat-cash').innerText = `Cash: $${res.data.cash.toFixed(2)}`;
        document.getElementById('stat-heat').innerText = `Heat: ${res.data.heat.toFixed(2)}%`;
    }

    if (res.html_view) {
        document.getElementById('view-container').innerHTML = res.html_view;
    }
}

function logToTerminal(msg, type = 'sys') {
    const log = document.getElementById('system-log');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    if (type === 'cmd') entry.style.borderLeftColor = '#06d6a0';
    entry.innerText = msg;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
}

function getMockMessage(cmd) {
    const helpTriggers = ['?', '-?', '--help'];
    const isHelp = helpTriggers.includes(cmd) || helpTriggers.some(t => cmd.endsWith(` ${t}`));

    if (cmd.startsWith('status') && !isHelp) return "Status updated. ✅";
    if (cmd.startsWith('panic') && !isHelp) return "🚨 ALL POSITIONS LIQUIDATED.";
    if (cmd.startsWith('close') && !isHelp) return `Executing close for ${cmd.split(' ')[1]}... 📝`;

    if (isHelp) {
        const tokens = cmd.split(' ');
        const target = helpTriggers.includes(tokens[0]) ? null : tokens[0];
        if (!target) return "Root Commands: status, close, panic, wizard, ?";
        if (cmd === 'status ?') return "--- COMMAND: status ---\nSYNTAX: status\nDESCRIPTION: Refreshes snapshot. Watch the Heat Index! Keep it under 10%.";
        if (cmd === 'close ?') return "--- COMMAND: close <idx/ticker/all> ---\nSYNTAX: close 1 (Speed is key in volatile markets).";
        if (cmd === 'cancel ?') return "--- COMMAND: cancel <idx/ticker/all> ---\nSYNTAX: cancel MSFT (Safest way to clear order book).";
        if (cmd === 'size ?') return "--- COMMAND: size <ticker> <entry> <stop> ---\nEXPERT TIP: Sizing is the ONLY factor you truly control.";
        if (cmd === 'panic ?') return "--- COMMAND: panic ---\n🚨 EMERGENCY: Market-closes everything immediately.";
        const helpMap = {
            'status': "COMMAND: status\\nDESCRIPTION: Fetches the latest portfolio data from the broker and recalculates all risk metrics.\\nUSE CASE: Run this to refresh the Main Stage dashboard with your current PnL and account health.",
            'close': "COMMAND: close <idx/ticker/all>\\nSYNTAX:\\n  close 1         -> Closes the position at index #1 in the table.\\n  close AAPL      -> Closes the position for Apple Inc.\\n  close all       -> Closes all current positions (Confirm required).\\n\\nDESCRIPTION: Sends a market order to liquidiate the specified position.",
            'panic': "COMMAND: panic\\nDESCRIPTION: ⚠️ EMERGENCY LIQUIDATION. Market-closes EVERY open position and cancels EVERY active order immediately.",
            'wizard': "COMMAND: wizard\\nDESCRIPTION: Launches the interactive Risk Management Wizard on the Main Stage for guided position planning.",
            'orders': "--- COMMAND: orders [cancel <target>] ---\nSYNTAX:\n  orders           -> View active orders.\n  orders cancel 1  -> Cancel order #1.\nDESCRIPTION: Manages pending orders. Alias: 'order'.\nEXPERT TIP: Check 'orders' before 'panic' to ensure no orphan orders remain.",
            'trades': "--- COMMAND: trades ---\nSYNTAX: trades\nDESCRIPTION: Lists all open positions with unique index (#).\nEXPERT TIP: Use this to verify active exposure before new trades.",
            'size': "--- COMMAND: size <ticker> <entry> <stop> ---\nDESCRIPTION: Calculates quantity based on 1% risk.\nEXPERT TIP: Sizing is the ONLY factor you can truly control.",
            'risk': "--- COMMAND: risk <ticker> --stop <p> ---\nDESCRIPTION: Predicts impact on Portfolio Heat.\nEXPERT TIP: Use this to plan 'Stop Trails' without over-leveraging.",
            'connect': "COMMAND: connect <env>\\nDESCRIPTION: Initializes the connection to the Broker Bridge (paper/live).",
            'disconnect': "COMMAND: disconnect\\nDESCRIPTION: Safely closes the socket connection to the broker.",
            'history': "COMMAND: history [days]\\nDESCRIPTION: Generates an equity curve and drawdown chart.",
            'stats': "COMMAND: stats [period]\\nDESCRIPTION: Calculates performance analytics (Winrate, Profit Factor)."
        };
        return helpMap[target] || `No detailed help for '${target}'.`;
    }
    return `Command received: ${cmd}`;
}

function getMockHtml(cmd) {
    const helpTriggers = ['?', '-?', '--help'];
    const isRootHelp = helpTriggers.includes(cmd);

    if (isRootHelp) {
        return `
            <div class='help-view' style='padding: 15px; background: #1e1e22; border-radius: 8px; border: 1px solid #333;'>
                <h2 style='color: #06d6a0; margin-top: 0;'>🚀 Trading Console Help</h2>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 20px;'>
                    <div>
                        <h3>Monitoring</h3>
                        <ul style='list-style: none; padding: 0;'>
                            <li><b>status</b> - Portfolio overview</li>
                            <li><b>trades</b> - Open positions</li>
                            <li><b>orders</b> - Pending orders</li>
                        </ul>
                    </div>
                    <div>
                        <h3>Execution</h3>
                        <ul style='list-style: none; padding: 0;'>
                            <li><b>close [idx]</b> - Liquidate</li>
                            <li><b>orders cancel [idx]</b> - Cancel</li>
                            <li><b>panic</b> - ⚠️ Liquidate All</li>
                        </ul>
                    </div>
                </div>
                <p style="margin-top:10px; font-size:0.8rem; color:#888;">Type <code>[cmd] ?</code> for details.</p>
            </div>
        `;
    }
    if (cmd.startsWith('status')) {
        return `
            <div class="status-view">
                <h2>Portfolio Snapshot</h2>
                <table border="0" style="width:100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
                    <thead style="background: #2a2a2e; color: #a0a0a0;">
                        <tr><th>#</th><th>Symbol</th><th>Qty</th><th>PnL</th><th>Risk</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>1</td><td>AAPL</td><td>100</td><td>+$450.00</td><td>0.45%</td></tr>
                        <tr><td>2</td><td>TSLA</td><td>50</td><td>-$120.00</td><td>0.80%</td></tr>
                    </tbody>
                </table>
                <br>
                <h3>Active Orders</h3>
                <table border="0" style="width:100%; border-collapse: collapse; text-align: left; font-size: 0.8rem;">
                    <thead style="background: #2a2a2e; color: #a0a0a0;">
                        <tr><th>ID</th><th>Ticker</th><th>Action</th><th>Price</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>ord_1</td><td>AAPL</td><td>BUY</td><td>145.0</td></tr>
                    </tbody>
                </table>
            </div>
        `;
    }
    if (cmd.startsWith('orders')) {
        return `
            <div class="orders-view">
                <h2>Order Management</h2>
                <table border="0" style="width:100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
                    <thead style="background: #2a2a2e; color: #a0a0a0;">
                        <tr><th>#</th><th>ID</th><th>Ticker</th><th>Type</th><th>Qty</th><th>Price</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>1</td><td>ord_1</td><td>AAPL</td><td>BUY</td><td>10</td><td>145.0</td></tr>
                        <tr><td>2</td><td>ord_2</td><td>TSLA</td><td>SELL</td><td>5</td><td>210.0</td></tr>
                    </tbody>
                </table>
                <p style="color: #a0a0a0; font-size: 0.8rem; margin-top: 10px;">Use CLI: <code>cancel &lt;#&gt;</code></p>
            </div>
        `;
    }
    return '';
}
