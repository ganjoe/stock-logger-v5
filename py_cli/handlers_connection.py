# py_cli/handlers_connection.py
from typing import List
from .models import CLIContext, CommandResponse, CLIMode
from .commands import ICommand, registry
from py_captrader import session, services
from py_captrader.adapter import CapTraderAdapter

class ConnectCommand(ICommand):
    name = "connect"
    description = "Connects to IBKR Gateway."
    syntax = "connect [ip] [port] [client_id]"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        # Defaults
        host = "127.0.0.1"
        port = 4002
        client_id = 0
        
        if len(args) >= 1: host = args[0]
        if len(args) >= 2: port = int(args[1])
        if len(args) >= 3: client_id = int(args[2])
        
        try:
            if session.is_connected():
                return CommandResponse(False, message="Already connected. Disconnect first.")
                
            session.connect(host=host, port=port, client_id=client_id)
            
            # Re-Register Adapter (Important if session changed)
            client = session.get_active_client()
            adapter = CapTraderAdapter(client)
            services.register_broker(adapter)
            
            return CommandResponse(True, message=f"Connected to {host}:{port} (ID: {client_id})")
        except Exception as e:
            return CommandResponse(False, message=f"Connection failed: {str(e)}", error_code="CONNECTION_ERROR")

class DisconnectCommand(ICommand):
    name = "disconnect"
    description = "Disconnects from IBKR Gateway."
    syntax = "disconnect"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        try:
             if not session.is_connected():
                 return CommandResponse(True, message="Already disconnected.")
                 
             session.disconnect()
             return CommandResponse(True, message="Disconnected.")
        except Exception as e:
             return CommandResponse(False, message=f"Error disconnecting: {e}")

# Register
registry.register(ConnectCommand())
registry.register(DisconnectCommand())
