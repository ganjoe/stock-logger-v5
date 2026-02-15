# py_cli/handlers_user_mode.py
from typing import List
from .models import CLIContext, CommandResponse, CLIMode
from .commands import ICommand, registry

class UserModeCommand(ICommand):
    name = "user"
    description = "Switches between 'pta' (Bot Mode) and 'human' (Pretty Print, Menus)."
    syntax = "user <pta|human>"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        if not args:
            return CommandResponse(
                True, 
                message=f"Current User Mode: {ctx.mode.value}",
                payload={"mode": ctx.mode.value}
            )

        new_mode_str = args[0].lower()
        
        if new_mode_str == "pta":
            ctx.mode = CLIMode.BOT
            return CommandResponse(
                True, 
                message="Switched to PTA (Bot) Mode. Output is now JSON.",
                payload={"mode": "BOT", "status": "active"}
            )
            
        elif new_mode_str == "human":
            ctx.mode = CLIMode.HUMAN
            # In a real implementation we would render a menu here
            return CommandResponse(
                True, 
                message=f"Switched to Human Mode (Pretty Print).",
                payload={"mode": "HUMAN"}
            )
            
        else:
            return CommandResponse(False, message="Usage: user <pta|human>", error_code="INVALID_MODE")

# Register
registry.register(UserModeCommand())
