#!/usr/bin/env python3
import os
import json
import time
import sys
import argparse
from py_cli.controller import CLIController, CLIMode
from py_captrader import services
from py_pta.bridge import PTABridge
from py_pta.telnet_client import TelChatClient

# 1. Setup CLI Context (Required by PTA to execute commands)
import py_cli.handlers_monitor
import py_cli.handlers_execution
import py_cli.handlers_trade
import py_cli.handlers_history
import py_cli.handlers_analytics
import py_cli.handlers_pta
import py_cli.handlers_connection

def main():
    # Load Default Telnet Configuration
    config_path = os.path.join(os.path.dirname(__file__), "py_pta", "telnet_config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except Exception:
        config = {}

    parser = argparse.ArgumentParser(description="PTA Telnet Agent - Connects the Trading System to the TelChat Hub.")
    parser.add_argument("--host", default=config.get("host", "127.0.0.1"), help="TelChat Hub Host")
    parser.add_argument("--port", type=int, default=config.get("port", 9999), help="TelChat Hub Port")
    parser.add_argument("--alias", default=config.get("alias", "pta"), help="Alias to register with at the hub")
    
    args = parser.parse_args()

    print(f"🚀 Starting PTA Telnet Agent (Alias: {args.alias})...")
    
    # Initialize CLI Controller in Bot Mode
    controller = CLIController(mode=CLIMode.BOT)
    services.register_cli(controller)
    
    # Initialize PTA Bridge
    bridge = PTABridge(controller)
    
    # Setup Telnet Client
    client = TelChatClient(
        host=args.host,
        port=args.port,
        alias=args.alias
    )
    
    # Define message callback
    def on_message(msg):
        msg_type = msg.get("msg_type")
        if msg_type == "data":
            sender, response_text = bridge.handle_hub_message(msg)
            print(f"  [PTA] Proccessed message from {sender}. Sending response...")
            client.send(to=sender, msg_type="data", data={"text": response_text})
        elif msg_type == "error":
            print(f"  [PTA] Received hub error: {msg.get('data')}")

    client.on_message_callback = on_message
    
    # Connect to Hub
    if not client.connect():
        print("❌ Failed to connect to TelChat Hub.")
        sys.exit(1)

    print("📡 PTA Agent is online and listening...")
    
    try:
        while client.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping PTA Agent...")
        client.stop()

if __name__ == "__main__":
    main()
