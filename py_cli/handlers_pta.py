from typing import List
from py_cli.models import CLIContext, CommandResponse, CLIMode
from py_cli.commands import ICommand, registry
from py_pta.bridge import PTABridge

# Global bridge instance to maintain chat history during CLI session
_bridge = None

class PTACommand(ICommand):
    name = "pta"
    description = "Interagiert mit dem Gemini Personal Trading Assistant."
    syntax = "pta <anweisung/frage>"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        global _bridge
        if not args:
            return CommandResponse(False, "Bitte gib eine Anweisung oder Frage ein. Beispiel: pta 'Wie sieht mein Portfolio aus?'")

        if _bridge is None:
            from py_captrader import services
            _bridge = PTABridge(services.get_cli())

        user_msg = " ".join(args)
        print(f"  [CLI] Sende Nachricht an Gemini...")
        
        response = _bridge.chat(user_msg)
        
        return CommandResponse(True, message=response)

# Register
registry.register(PTACommand())
