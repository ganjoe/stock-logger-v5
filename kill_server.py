import os
import signal
import subprocess
import sys

def kill_server():
    """Kills any process running http.server on port 8000."""
    print("Searching for running web server on port 8000...")
    try:
        # Use subprocess.run to avoid exception if no process is found (exit code 1)
        result = subprocess.run(["lsof", "-ti", "tcp:8000"], capture_output=True, text=True)
        output = result.stdout.strip()
        
        if output:
            pids = output.split('\n')
            for pid in pids:
                print(f"Stopping process {pid}...")
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass
            print("Server stopped. ✅")
        else:
            print("Port 8000 is already free. No server found. 👍")
    except Exception as e:
        print(f"Error while checking port 8000: {e}")

if __name__ == "__main__":
    kill_server()
