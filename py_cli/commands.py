"""
py_cli/commands.py
Command Registry and Interface Definition.
Decouples command logic from the controller.
"""
from typing import Protocol, List, Dict, Optional, Type
from .models import CLIContext, CommandResponse

class ICommand(Protocol):
    """ Interface that all CLI commands must implement. """
    name: str
    description: str
    syntax: str

    def execute(self, ctx: CLIContext, args: List[str]) -> CommandResponse:
        """ 
        Executes the command logic. 
        Returns structured CommandResponse.
        """
        ...

class CommandRegistry:
    """ 
    Central registry for all CLI commands. 
    Implements the Singleton pattern effectively via module-level instance usage or explicit instantiation.
    """
    def __init__(self):
        self._commands: Dict[str, ICommand] = {}
        self._aliases: Dict[str, str] = {}

    def register(self, command: ICommand, aliases: List[str] = None):
        """ Registers a command instance. Optional aliases. """
        self._commands[command.name] = command
        if aliases:
            for alias in aliases:
                self._aliases[alias] = command.name

    def get_command(self, name: str) -> Optional[ICommand]:
        """ Resolves command by name or alias. """
        if name in self._commands:
            return self._commands[name]
        
        if name in self._aliases:
            target_name = self._aliases[name]
            return self._commands.get(target_name)
            
        return None

    def list_commands(self) -> List[ICommand]:
        """ Returns list of all registered commands (sorted by name). """
        return sorted(list(self._commands.values()), key=lambda c: c.name)

# Global Instance for convenience
registry = CommandRegistry()
