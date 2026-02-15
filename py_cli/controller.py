"""
py_cli/controller.py
The "Brain" of the CLI. Handles the Input -> Parse -> Execute -> Render loop.
"""
import sys
import json
import traceback
from typing import List, Dict, Any, Optional
from .models import CLIContext, CLIMode, CommandResponse
from .commands import CommandRegistry, ICommand, registry as global_registry

class CLIController:
    def __init__(self, mode: CLIMode, registry: CommandRegistry = global_registry):
        self.context = CLIContext(mode=mode)
        self.registry = registry

    def process_input(self, input_str: str) -> str:
        """ 
        Main Loop Entry. 
        Returns FINAL output string (Formatted Text or JSON) ready for stdout.
        """
        if not input_str.strip():
            return ""

        try:
            # 1. Parse Input
            parts = input_str.strip().split()
            cmd_name = parts[0].lower()
            args = parts[1:]

            # 2. Resolve Command
            command = self.registry.get_command(cmd_name)
            if not command:
                return self._render_error(f"Unknown command: {cmd_name}", "UNKNOWN_COMMAND")

            # 3. Execute
            response = command.execute(self.context, args)
            
            # 4. Render
            return self._render_response(response)

        except Exception as e:
            # Catch-all for unhandled exceptions to prevent crash
            # Log trace for debug (stderr)
            sys.stderr.write(traceback.format_exc())
            return self._render_error(f"Internal Error: {str(e)}", "INTERNAL_ERROR")


    def _render_response(self, response: CommandResponse) -> str:
        """ Renders the response based on the current mode. """
        
        if self.context.mode == CLIMode.BOT:
            # BOT MODE: JSON ONLY
            output = {
                "success": response.success,
                "payload": response.payload,
                "message": response.message,
                "error_code": response.error_code
            }
            return json.dumps(output)
        else:
            # HUMAN MODE: PRETTY PRINT
            if not response.success:
                return f"❌ Error: {response.message} ({response.error_code})"
                
            # Success handling
            out = []
            if response.message:
                out.append(f"✅ {response.message}")
                
            if response.payload:
                # Basic JSON Pretty Print for now
                out.append(json.dumps(response.payload, indent=2, default=str))
                
            return "\n".join(out)

    def _render_error(self, message: str, code: str) -> str:
        """ Renders a generic error. """
        return self._render_response(CommandResponse(
            success=False,
            message=message,
            error_code=code
        ))
