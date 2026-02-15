"""
py_cli/models.py
Strict Data Structures (DTOs/Enums) for the CLI context.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional

class CLIMode(Enum):
    HUMAN = "HUMAN"
    BOT = "BOT"

@dataclass
class CLIContext:
    mode: CLIMode
    user_id: str = "cli_user"
    session_id: str = "default_session"
    confirm_all: bool = False # For --force/--confirm logic in Bot mode

@dataclass
class CommandResponse:
    success: bool
    message: str          # To be displayed to Human (Formatted Text)
    data: Optional[Dict[str, Any]] = None # To be serialized for Bot (JSON)
    error_code: str = "OK" # Standardized Error Code for Bots
