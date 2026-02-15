import sys
import os
import webbrowser
import subprocess
import time
import signal

# Add the root directory to PYTHONPATH to allow imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from py_interface.processor import CommandProcessor
from datetime import datetime
from dataclasses import dataclass
from typing import List

# --- Mock Implementations for Independent Testing ---

@dataclass
class MockPosition:
    ticker: str
    quantity: float
    avg_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float

@dataclass
class MockSnapshot:
    timestamp: datetime
    equity: float
    cash: float
    positions: List[MockPosition]
    total_risk: float
    active_orders: List = None

class MockBroker:
    def get_portfolio_snapshot(self):
        return MockSnapshot(
            timestamp=datetime.now(),
            equity=52430.50,
            cash=12000.00,
            positions=[
                MockPosition("AAPL", 100, 150.0, 154.50, 15450.0, 450.0),
                MockPosition("TSLA", 50, 200.0, 197.60, 9880.0, -120.0),
            ],
            total_risk=750.0,
            active_orders=[]
        )

    def execute_trade(self, symbol, qty, action):
        print(f"DEBUG: Broker executing {action} for {qty} shares of {symbol}")
        return True

    def generate_orders(self):
        return [
            {"id": "ord_1", "ticker": "AAPL", "action": "BUY", "qty": 10, "price": 145.0, "status": "Submitted"},
            {"id": "ord_2", "ticker": "TSLA", "action": "SELL", "qty": 5, "price": 210.0, "status": "PreSubmitted"},
        ]

    def get_active_orders(self):
        return self.generate_orders()

    def cancel_order(self, order_id):
        print(f"DEBUG: Broker cancelling order {order_id}")
        return True

    def connect(self, env):
        print(f"DEBUG: Broker connecting to {env}...")
        return True

    def disconnect(self):
        print("DEBUG: Broker disconnecting...")
        return True

class MockAnalytics:
    def analyze(self, snapshot):
        from py_analytics.capture import SnapshotAnalyzer
        return SnapshotAnalyzer().analyze(snapshot)

def start_web_server():
    """Starts the Python HTTP server in the background."""
    print("Starting Web Server on http://localhost:8000...")
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "http.server", "8000"],
            cwd=os.path.join(os.path.dirname(__file__), "web"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1) # Wait for server
        webbrowser.open("http://localhost:8000")
        return process
    except Exception as e:
        print(f"Failed to start web server: {e}")
        return None

def run_cli():
    server_process = start_web_server()
    
    print("\n=== Trading Interface CLI Runner ===")
    print("Type '?' for help or 'exit' to quit.")
    
    broker = MockBroker()
    analytics = MockAnalytics()
    processor = CommandProcessor(broker, analytics)
    
    while True:
        try:
            cmd_input = input("\n> ").strip()
            if cmd_input.lower() in ["exit", "quit"]:
                break
            
            if not cmd_input:
                continue

            result = processor.process(cmd_input)
            
            # Print Text Message
            if result.success:
                print(f"SUCCESS: {result.message}")
            else:
                print(f"ERROR: {result.message}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")

    if server_process:
        print("\nStopping web server...")
        server_process.terminate()

if __name__ == "__main__":
    run_cli()
