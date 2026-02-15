"""
main_cli.py
Unified Entry Point for the Trading System.
Modes:
 - Interactive (Human): Standard Shell
 - Bot (JSON): Input via args or stdin, output via stdout (JSON)
"""
import sys
import argparse
from py_cli.models import CLIMode
from py_cli.controller import CLIController
# Import handlers to trigger registration
import py_cli.handlers_monitor
import py_cli.handlers_execution

def main():
    parser = argparse.ArgumentParser(description="Trading System Unified CLI")
    parser.add_argument("--mode", choices=["human", "bot"], default="human", help="Operating Mode")
    parser.add_argument("--confirm-all", action="store_true", help="Auto-confirm critical actions (Bot only)")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to execute")

    args = parser.parse_args()

    # 1. Setup Context
    mode = CLIMode.BOT if args.mode == "bot" else CLIMode.HUMAN
    controller = CLIController(mode=mode)
    controller.context.confirm_all = args.confirm_all

    # 2. Execution
    # If arguments are provided, execute single command and exit
    if args.command:
        # Join the remainder args back into a string
        # e.g. ['status'] -> "status"
        # e.g. ['order', 'buy', 'AAPL'] -> "order buy AAPL"
        input_str = " ".join(args.command)
        response = controller.process_input(input_str)
        print(response)
        return

    # 3. Interactive Loop (Only for Human Mode)
    if mode == CLIMode.HUMAN:
        print(f"🚀 Trading CLI (Mode: {mode.value})")
        print("Type 'exit' or 'quit' to stop.")
        while True:
            try:
                user_input = input(">> ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                response = controller.process_input(user_input)
                print(response)
            except KeyboardInterrupt:
                print("\nExiting...")
                break
    else:
        # Bot Mode without args? Expect stdin? 
        # For now, just print error if no command passed
        print('{"success": false, "message": "No command provided", "error_code": "NO_INPUT"}')
        sys.exit(1)

if __name__ == "__main__":
    main()
