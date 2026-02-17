"""
test_dashboard_flow.py
Simulates the sequence of CLI commands the PTA uses to visualize a chart in the dashboard.
"""
from py_cli.controller import CLIController, CLIMode
from py_captrader import services

# Import handlers to ensure they are registered
import py_cli.handlers_monitor
import py_cli.handlers_connection
import py_cli.handlers_dashboard

def run_test():
    # 1. Setup Controller in HUMAN mode with a unique Client ID for testing
    # We use 98 to not collide with the PTA (99) or TWS default (0)
    controller = CLIController(mode=CLIMode.HUMAN)
    controller.context.client_id = 98 
    services.register_cli(controller)

    # 2. Sequential Commands
    import sys
    skip_server = "--skip-server" in sys.argv
    
    if not skip_server:
        print(">>> Executing CLI: dashboard --stop")
        print(controller.process_input("dashboard --stop"))
    
        print("\n>>> Executing CLI: dashboard --start")
        print(controller.process_input("dashboard --start"))
        import time
        print("  [Test] Waiting 2s for server startup...")
        time.sleep(2) # Give FastAPI time to bind to port
    else:
        print(">>> Skipping Server Start/Stop (--skip-server)")

    commands = [
        "connect 127.0.0.1 4002 98",# Correct syntax: host port clientId
        "chart ONDS --to-dashboard"   # Fetch data and PIPE directly
    ]

    print("=== PTA Dashboard Visualization Flow Test ===")
    
    for cmd in commands:
        print(f"\n>>> Executing CLI: {cmd}")
        response = controller.process_input(cmd)
        print(response)

if __name__ == "__main__":
    run_test()
