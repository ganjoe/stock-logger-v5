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

class ChatCommand(ICommand):
    name = "chat"
    description = "Startet einen interaktiven Chat mit Gemini (beenden mit 'exit')."
    syntax = "chat"

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        global _bridge
        if _bridge is None:
            from py_captrader import services
            _bridge = PTABridge(services.get_cli())

        print("  [CLI] Starte Chat-Modus. Tippe 'exit' zum Beenden.")
        
        while True:
            try:
                user_input = input("(Gemini) >> ").strip()
                if not user_input:
                    continue
                
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                print(f"  ... denke nach ...")
                response = _bridge.chat(user_input)
                print(f"{response}\n")
                
            except KeyboardInterrupt:
                print("\nChat beendet.")
                break
            except EOFError:
                break

        return CommandResponse(True, "Chat-Modus beendet.")

registry.register(ChatCommand())
