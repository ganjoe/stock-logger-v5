"""
run_dashboard_foreground.py
Simple wrapper to run the dashboard server in the foreground for debugging.
"""
from py_dashboard.server import run_http_server

if __name__ == "__main__":
    print("--- Starting Dashboard Server in FOREGROUND Mode (SSE) ---")
    print("logs will be printed to stdout")
    
    # Run HTTP/SSE Server (Blocking)
    try:
        run_http_server()
    except KeyboardInterrupt:
        print("Stopping.")
