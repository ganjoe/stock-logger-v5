import os
import json
import google.generativeai as genai
from typing import List, Dict, Any, Optional

class GeminiPTA:
    """
    Personal Trading Assistant powered by Google Gemini.
    Handles conversation and tool calling via the CLI bridge.
    """
    def __init__(self, config_path: str = "secrets/gemini_config.json"):
        self.config_path = config_path
        self.api_key = self._load_api_key()
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use a model that supports function calling well
            self.model = genai.GenerativeModel('gemini-flash-latest')
        else:
            self.model = None

    def _load_api_key(self) -> Optional[str]:
        if not os.path.exists(self.config_path):
            return None
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
                return config.get("api_key")
        except Exception:
            return None

    def is_configured(self) -> bool:
        return self.api_key is not None

    def get_chat_response(self, message: str, chat_history: List[Dict[str, Any]] = None, tools: List[Any] = None) -> Any:
        """
        Sends a message to the model and returns the response (which might include tool calls).
        """
        if not self.model:
            raise RuntimeError("Gemini API Key missing. Please check secrets/gemini_config.json")

        chat = self.model.start_chat(history=chat_history or [])
        response = chat.send_message(message, tools=tools)
        return response

    def count_tokens(self, content: Any) -> int:
        """Counts tokens for the given content."""
        if not self.model:
            return 0
        try:
            return self.model.count_tokens(content).total_tokens
        except Exception:
            return 0
