"""
main_matrix.py
Entry point for the Matrix Chat Bot.
Bridges Matrix messages to the PTA via the existing CLIController + PTABridge.

Usage:
    python main_matrix.py
"""
import asyncio
import sys

from py_cli.models import CLIMode
from py_cli.controller import CLIController
from py_captrader import services

# Import handlers to trigger command registration
import py_cli.handlers_monitor
import py_cli.handlers_execution
import py_cli.handlers_trade
import py_cli.handlers_history
import py_cli.handlers_analytics
import py_cli.handlers_pta
import py_cli.handlers_connection
import py_cli.handlers_dashboard

from py_pta.bridge import PTABridge
from py_matrix.config import load_config
from py_matrix.bot import MatrixBot


def main():
    print("🤖 Stock-Logger v5 – Matrix Bot Mode")
    print("=" * 40)

    # 1. Load Matrix Config
    config = load_config()
    if config is None:
        print("❌ Matrix config not found. Create 'secrets/matrix_config.json'.")
        sys.exit(1)

    if not config.validate():
        print("❌ Matrix config incomplete. Check homeserver, user_id, password, room_id.")
        sys.exit(1)

    print(f"[Setup] Homeserver: {config.homeserver}")
    print(f"[Setup] User:       {config.user_id}")
    print(f"[Setup] Room:       {config.room_id}")

    # 2. Setup CLI Controller (BOT mode = JSON output)
    controller = CLIController(mode=CLIMode.BOT)
    services.register_cli(controller)

    # 3. Create PTA Bridge
    bridge = PTABridge(controller)
    print("[Setup] ✅ PTABridge initialized")

    # 4. Create and run Matrix Bot
    bot = MatrixBot(config, bridge)

    print("[Setup] 🚀 Starting Matrix sync loop...")
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n🛑 Matrix Bot stopped.")


if __name__ == "__main__":
    main()
