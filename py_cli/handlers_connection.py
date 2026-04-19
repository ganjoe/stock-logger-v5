# py_cli/handlers_connection.py
from typing import List
from .models import CLIContext, CommandResponse, CLIMode
from .commands import ICommand, registry
from py_captrader import session, services
from py_captrader.config import (
    DEFAULT_HOST, DEFAULT_PORT, DEFAULT_CLIENT_ID
)
from py_captrader.adapter import CapTraderAdapter

class ConnectCommand(ICommand):
    name = "connect"
    description = "Connects to IBKR Gateway."
    syntax = "connect [host|default] [port] [client_id]"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        # Defaults
        host = DEFAULT_HOST
        port = DEFAULT_PORT
        client_id = DEFAULT_CLIENT_ID
        
        if len(args) >= 1:
            val = args[0].lower()
            if val != "default":
                host = args[0]
        
        if len(args) >= 2: port = int(args[1])
        if len(args) >= 3: client_id = int(args[2])
        
        try:
            if session.is_connected():
                # Check if we are already connected to the SAME target
                client = session._ACTIVE_CLIENT
                if client and client.host == host and client.port == port:
                     return CommandResponse(success=True, message=f"Already connected to {host}:{port}.")
                
                # Different target -> Auto-disconnect
                session.disconnect()
                
            session.connect(host=host, port=port, client_id=client_id)
            
            # Re-Register Adapter (Important if session changed)
            client = session.get_active_client()
            adapter = CapTraderAdapter(client)
            services.register_broker(adapter)
            
            return CommandResponse(success=True, message=f"Connected to {host}:{port} (ID: {client_id})")
        except Exception as e:
            return CommandResponse(success=False, message=f"Connection failed: {str(e)}", error_code="CONNECTION_ERROR")

class DisconnectCommand(ICommand):
    name = "disconnect"
    description = "Disconnects from IBKR Gateway."
    syntax = "disconnect"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        try:
             if not session.is_connected():
                  return CommandResponse(success=True, message="Already disconnected.")
                 
             session.disconnect()
             return CommandResponse(success=True, message="Disconnected.")
        except Exception as e:
              return CommandResponse(success=False, message=f"Error disconnecting: {e}")

# Register
registry.register(ConnectCommand())
registry.register(DisconnectCommand())
