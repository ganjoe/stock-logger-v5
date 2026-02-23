"""
py_matrix/config.py
Loads Matrix credentials from secrets/matrix_config.json.
"""
import os
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class MatrixConfig:
    homeserver: str
    user_id: str
    password: str
    room_id: str

    def validate(self) -> bool:
        """Returns True if all required fields are non-empty."""
        return all([self.homeserver, self.user_id, self.password, self.room_id])


def load_config(config_path: str = "secrets/matrix_config.json") -> Optional[MatrixConfig]:
    """
    Loads Matrix configuration from JSON file.
    Returns None if the file does not exist or is invalid.
    """
    if not os.path.exists(config_path):
        return None

    try:
        with open(config_path, "r") as f:
            data = json.load(f)

        return MatrixConfig(
            homeserver=data.get("homeserver", ""),
            user_id=data.get("user_id", ""),
            password=data.get("password", ""),
            room_id=data.get("room_id", ""),
        )
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[Matrix] Config Error: {e}")
        return None
