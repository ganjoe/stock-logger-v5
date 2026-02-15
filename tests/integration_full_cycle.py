# tests/integration_full_cycle.py
import subprocess
import time
import json
import sys
import os

# --- Configurations ---
RUN_PAPER_SCRIPT = "run_paper.py"
TIMEOUT = 30  # Seconds to wait for responses
TICKER = "INTC"
LIMIT_PRICE = 10.0 # Way below market to stay pending
QUANTITY = 10

# --- Helper for Historical Scenario ---
def create_historical_scenarios():
    """Creates a dummy trade file with historical order logs."""
    history_ticker = "HIST_ORDER_TEST"
    trade_dir = f"data/trades/{history_ticker}"
    os.makedirs(trade_dir, exist_ok=True)
    
    # Dates
    from datetime import datetime, timedelta
    now = datetime.now()
    t_start = now - timedelta(days=10)
    t_mid = now - timedelta(days=5)
    t_end = now - timedelta(days=2)
    
    # Trade State with Order History:
    # 1. Order A (Submitted @ t_start) -> Cancelled @ t_mid
    # 2. Order B (Submitted @ t_mid) -> Filled @ t_end
    
    state = {
        "id": "HIST_SCENARIO_1",
        "ticker": history_ticker,
        "status": "OPEN", # Or CLOSED depending on fill logic, let's say OPEN with position
        "transactions": [
            {
               "id": "TX_B",
               "timestamp": t_end.isoformat(),
               "type": "ENTRY",
               "quantity": 10,
               "price": 100.0,
               "commission": 1.0,
               "slippage": 0.0
            }
        ],
        "active_orders": {}, # Currently no active orders
        "order_history": [
            # Order A: Submitted then Cancelled
            {
                "timestamp": t_start.isoformat(),
                "order_id": "ORD_A",
                "action": "BUY",
                "status": "SUBMITTED",
                "message": "Entry A",
                "quantity": 10,
                "type": "LMT",
                "limit_price": 99.0,
                "stop_price": None,
                "trigger_price": None,
                "note": "Initial A",
                "details": {}
            },
            {
                "timestamp": t_mid.isoformat(),
                "order_id": "ORD_A",
                "action": "CANCEL",
                "status": "CANCELLED",
                "message": "Cancelled A",
                "quantity": 0,
                "type": "CANCEL",
                "limit_price": None,
                "stop_price": None,
                "trigger_price": None,
                "note": "",
                "details": {}
            },
            # Order B: Submitted then Filled
            {
                "timestamp": t_mid.isoformat(),
                "order_id": "ORD_B",
                "action": "BUY",
                "status": "SUBMITTED",
                "message": "Entry B",
                "quantity": 10,
                "type": "LMT",
                "limit_price": 100.0,
                "stop_price": None,
                "trigger_price": None,
                "note": "Entry B",
                "details": {}
            },
            {
                "timestamp": t_end.isoformat(),
                "order_id": "ORD_B",
                "action": "BUY",
                "status": "FILLED",
                "message": "Filled B",
                "quantity": 10,
                "type": "FILL",
                "limit_price": 100.0,
                "stop_price": None,
                "trigger_price": None,
                "note": "",
                "details": {}
            }
        ]
    }
    
    with open(f"{trade_dir}/hist_trade.json", "w") as f:
        json.dump(state, f, indent=2)
        
    print(f"✅ Created historical scenario: {history_ticker}")
    return t_start, t_mid, t_end

def run_test():
    # Setup Data
    ts_start, ts_mid, ts_end = create_historical_scenarios()
    
    print(f"🚀 Launching {RUN_PAPER_SCRIPT}...")
    
    # Start Process
    # We need universal_newlines=True to handle strings instead of bytes
    # buffering=1 for line buffering
    process = subprocess.Popen(
        [sys.executable, "-u", RUN_PAPER_SCRIPT, "--client-id", "555"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=os.getcwd()
    )
    
    try:
        # 1. Wait for Startup
        print("Waiting for startup...")
        _wait_for_output(process, "🚀 Trading CLI", timeout=30)
        
        # 2. Switch to Bot Mode
        _send_command(process, "user pta")
        resp = _read_json_response(process)
        if not resp.get("success"): raise RuntimeError(f"Failed to switch to BOT mode: {resp}")
        
        # --- VERIFY HISTORICAL RECONSTRUCTION ---
        # Query at T_START + 1 day (Should show Order A Active, B not exist)
        # days_back logic in history command is imprecise (uses timedelta(days=N)).
        # Let's use N=8 (10 days ago + 2 = 8 days ago?)
        # T_START is -10 days. 
        # T_MID is -5 days.
        # T_END is -2 days.
        
        # Point 1: 7 days ago (Between START and MID) -> Order A should be active?
        # Actually T_Start=Now-10. T_Mid=Now-5.
        # Check at 7 days back.
        
        print("\n🔎 Verifying History @ 7 Days Ago (Expect Order A Active)...")
        _send_command(process, "history 7")
        resp = _read_json_response(process)
        if notCB(resp): raise RuntimeError(f"History 7 failed: {resp}")
        
        active_orders = resp["payload"].get("active_orders", [])
        # Provide logic to find 'ORD_A'
        found_a = any(o["order_id"] == "ORD_A" for o in active_orders)
        found_b = any(o["order_id"] == "ORD_B" for o in active_orders)
        
        if not found_a:
             print(f"DEBUG FULL RESP: {json.dumps(resp, indent=2)}")
             raise AssertionError("Order A should be active 7 days ago!")
        if found_b:
             raise AssertionError("Order B should NOT be active 7 days ago!")
        print("✅ Order A correctly identified as active in history.")

        # Point 2: 3 days ago (Between MID and END) -> Order B Active? Order A Cancelled?
        # T_Mid was -5. T_End is -2.
        # Check at 3 days back.
        print("\n🔎 Verifying History @ 3 Days Ago (Expect Order B Active, A Gone)...")
        _send_command(process, "history 3")
        resp = _read_json_response(process)
        if notCB(resp): raise RuntimeError(f"History 3 failed: {resp}")
        
        active_orders = resp["payload"].get("active_orders", [])
        found_a = any(o["order_id"] == "ORD_A" for o in active_orders)
        found_b = any(o["order_id"] == "ORD_B" for o in active_orders)
        
        if found_a:
             raise AssertionError("Order A should be CANCELLED 3 days ago!")
        if not found_b:
             print(f"Payload: {active_orders}")
             raise AssertionError("Order B should be active 3 days ago!")
        print("✅ Order B correctly identified as active (A gone).")

        # Point 3: 0 days ago (Now) -> No active orders (B filled)
        print("\n🔎 Verifying History @ Now (Expect No Active Orders)...")
        _send_command(process, "history 0")
        resp = _read_json_response(process)
        
        active_orders = resp["payload"].get("active_orders", [])
        if active_orders:
             # Check if they are OUR test orders
             if any(o["order_id"] in ["ORD_A", "ORD_B"] for o in active_orders):
                 raise AssertionError(f"Orders A/B should be closed! Found: {active_orders}")
        print("✅ Orders correctly closed in present time.")
             
        
        # Continue with Live Trade Test...
        print("\n🚀 Proceeding with Live Trade Test...")
        # ... (Rest of original test)
        cmd = json.dumps({
            "action": "ENTER",
            "ticker": TICKER,
            "quantity": QUANTITY,
            "limit_price": LIMIT_PRICE
        })
        _send_command(process, f"trade {cmd}")
        
        resp = _read_json_response(process)
        if notCB(resp):
             print(f"❌ Trade Enter Failed: {resp}")
             sys.exit(1)
             
        trade_id = resp["payload"]["trade_id"]
        order_id = resp["payload"]["broker_order_id"]
        print(f"✅ Trade Entered. ID: {trade_id}, Order: {order_id}")
        
        # 4. Wait a bit (simulate bot thinking)
        time.sleep(2)
        
        # 5. Cancel Trade
        cmd = json.dumps({
            "action": "CANCEL",
            "trade_id": trade_id,
            "ticker": TICKER,
            "broker_order_id": order_id
        })
        _send_command(process, f"trade {cmd}")
        
        resp = _read_json_response(process)
        if notCB(resp):
             print(f"❌ Trade Cancel Failed: {resp}")
             sys.exit(1)
             
        assert resp["payload"]["status"] == "CANCELLED"
        print(f"✅ Trade Cancelled.")
        
        # --- NEW: Verify Chart Download ---
        chart_path = os.path.join(os.getcwd(), "data/market_cache/INTC/charts/1D.json")
        print(f"Checking for chart file at: {chart_path}")
        if not os.path.exists(chart_path):
             raise RuntimeError(f"Chart file not found at {chart_path}. Auto-download failed?")
        print("✅ Chart file found (Auto-Download Verified).")
        
        # --- NEW: Verify History Command ---
        print("Running history command...")
        _send_command(process, "history 0") 
        resp = _read_json_response(process)
        
        if notCB(resp):
             raise RuntimeError(f"History command failed: {resp}")
        
        print(f"✅ History Command Response: {resp.get('message')}")
        
        # 6. Exit
        _send_command(process, "exit")
        print("✅ Test Completed Successfully.")
        
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        # Kill process
        process.kill()
        sys.exit(1)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

def _wait_for_output(process, content, timeout):
    start = time.time()
    buffer = ""
    while time.time() - start < timeout:
        # Read line by line non-blocking is tricky with standard read/readline
        # But stdout is PIPE. readline() blocks until newline.
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                raise RuntimeError("Process exited unexpectedly.")
            continue
            
        buffer += line
        print(f"[RunPaper] {line.strip()}") 
        
        if content in line:
            return True
    
    raise TimeoutError(f"Did not find '{content}' in output within {timeout}s.\nBuffer:\n{buffer}")

def _send_command(process, cmd):
    print(f"Sending: {cmd}")
    process.stdin.write(cmd + "\n")
    process.stdin.flush()

def _read_json_response(process):
    # We expect the next line (or one of the next lines) to be valid JSON
    # The CLI might print prompts or other info.
    # We scan for '{'
    
    start = time.time()
    while time.time() - start < 60:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                # Process dead. Read stderr for clues
                err = process.stderr.read()
                raise RuntimeError(f"Process exited. STDERR:\n{err}")
            continue
            
        line = line.strip()
        # Find JSON boundaries
        if "{" in line and "}" in line:
            try:
                start = line.index("{")
                end = line.rindex("}") + 1
                json_part = line[start:end]
                return json.loads(json_part)
            except:
                print(f"[RunPaper] {line}")
        else:
            if line:
                print(f"[RunPaper] {line}")
                
    raise TimeoutError("No JSON response received.")

def notCB(resp):
    return resp.get("success") is not True

if __name__ == "__main__":
    run_test()
