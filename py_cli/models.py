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
    payload: Optional[Dict[str, Any]] = None # Core Data (Bot-First)
    message: Optional[str] = None            # Human Readable (Optional)
    error_code: str = "OK"                   # Machine Error Code
