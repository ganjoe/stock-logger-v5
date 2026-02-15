import subprocess
import os
import sys
import time
import webbrowser

def restart_server():
    """Restarts the web server by killing any existing process and starting a new one."""
    print("=== Restarting Trading Dashboard Server ===")
    
    # 1. Kill any existing server
    try:
        subprocess.run([sys.executable, "kill_server.py"], check=True)
    except Exception as e:
        print(f"Warning: Could not run kill_server.py: {e}")

    # 2. Start new server
    print("\nStarting new server instance...")
    try:
        # Ensure we are in the root directory context
        root_dir = os.path.dirname(os.path.abspath(__file__))
        web_dir = os.path.join(root_dir, "web")
        
        process = subprocess.Popen(
            [sys.executable, "-m", "http.server", "8000"],
            cwd=web_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait a moment for server to initialize
        time.sleep(1.5)
        
        # Open Browser
        url = "http://localhost:8000"
        print(f"Server started on {url} (PID: {process.pid})")
        webbrowser.open(url)
        print("\nDashboard opened in your default browser. ✅")
        
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to start server: {e}")

if __name__ == "__main__":
    restart_server()
