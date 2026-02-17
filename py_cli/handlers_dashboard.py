"""
py_cli/handlers_dashboard.py
CLI Command for interacting with the local Web Dashboard.
"""
import requests
import json
import argparse
import sys
import os
import subprocess
import signal
import time
from typing import List
from .models import CLIContext, CommandResponse
from .commands import ICommand, registry

PID_FILE = "py_dashboard/server.pid"

class DashboardCommand(ICommand):
    name = "dashboard"
    description = "Pushes data to or manages the local browser dashboard."
    syntax = "dashboard [--start | --stop | --type TYPE --data JSON]"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        parser = argparse.ArgumentParser(prog="dashboard", add_help=False)
        parser.add_argument("--start", action="store_true", help="Start the dashboard server")
        parser.add_argument("--stop", action="store_true", help="Stop the dashboard server")
        parser.add_argument("--type", type=str, help="Type of data (e.g. PNL, PRICE)")
        parser.add_argument("--data", type=str, help="JSON string of data points")
        parser.add_argument("--clear", action="store_true", help="Clear the dashboard")
        parser.add_argument("--url", type=str, default="http://localhost:8000/broadcast", help="Server URL")

        try:
            cmd_args, _ = parser.parse_known_args(args)
            
            # 1. HANDLE START
            if cmd_args.start:
                if os.path.exists(PID_FILE):
                     return CommandResponse(False, message="Dashboard Server seems to be already running (PID file exists).", error_code="ALREADY_RUNNING")
                
                print("  [CLI] Starting Dashboard Server in background...")
                # Start as background process
                process = subprocess.Popen(
                    [sys.executable, "py_dashboard/server.py"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                
                # Write PID
                with open(PID_FILE, "w") as f:
                    f.write(str(process.pid))
                
                return CommandResponse(True, message=f"Dashboard Server started (PID: {process.pid}) at http://localhost:8000")

            # 2. HANDLE STOP
            if cmd_args.stop:
                if not os.path.exists(PID_FILE):
                    return CommandResponse(False, message="Dashboard Server is not running (PID file missing).", error_code="NOT_RUNNING")
                
                with open(PID_FILE, "r") as f:
                    pid = int(f.read().strip())
                
                try:
                    os.kill(pid, signal.SIGTERM)
                    os.remove(PID_FILE)
                    return CommandResponse(True, message="Dashboard Server stopped.")
                except ProcessLookupError:
                    os.remove(PID_FILE)
                    return CommandResponse(False, message="Process not found, PID file removed.", error_code="ZOMBIE_PID")

            # 3. HANDLE DATA PUSH
            if cmd_args.clear:
                payload = {
                    "msg_type": "CLEAR",
                    "payload_type": "None",
                    "data": []
                }
            elif cmd_args.type and cmd_args.data:
                try:
                    data_obj = json.loads(cmd_args.data)
                except json.JSONDecodeError:
                    return CommandResponse(False, message="Invalid JSON in --data", error_code="JSON_ERROR")
                
                payload = {
                    "msg_type": "CHART_UPDATE",
                    "payload_type": cmd_args.type.upper(),
                    "data": data_obj
                }
            else:
                return CommandResponse(False, message="Missing --type and --data, or --start/--stop/--clear", error_code="INVALID_ARGS")

            # Send to local server
            resp = requests.post(cmd_args.url, json=payload, timeout=2)
            if resp.status_code == 200:
                return CommandResponse(True, message=f"Pushed {payload['payload_type']} to Dashboard.", payload=resp.json())
            else:
                return CommandResponse(False, message=f"Server error: {resp.status_code}", error_code="SERVER_ERROR")

        except requests.exceptions.ConnectionError:
            return CommandResponse(False, message="Dashboard Server not running (localhost:8000). Use 'dashboard --start'.", error_code="CONN_ERROR")
        except Exception as e:
            return CommandResponse(False, message=f"Dashboard Error: {str(e)}", error_code="INTERNAL_ERROR")

# Registration
registry.register(DashboardCommand())
