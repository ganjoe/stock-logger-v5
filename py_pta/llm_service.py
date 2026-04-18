import json
import requests
from openai import OpenAI

class LLMService:
    """
    Standalone wrapper for the LM Studio / OpenAI API communication.
    Supports dependency injection for configuration and tools.
    Maintains its own conversation history (context memory).
    """
    def __init__(self, base_url: str, model_name: str, system_prompt: str, tools_schema: list = None, tool_executor: callable = None, gpu_offload: str = "max"):
        self.base_url = base_url
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.gpu_offload = gpu_offload
        self.tools_schema = tools_schema
        self.tool_executor = tool_executor

        # Derive LM Studio Management API URL from the base URL
        base = self.base_url.rstrip('/')
        if base.endswith('/v1'):
            self.mgmt_url = base.replace('/v1', '/api/v1')
        else:
            self.mgmt_url = f"{base}/api/v1"

        # LM Studio usually doesn't need an API key, but the client requires a string.
        self.client = OpenAI(base_url=self.base_url, api_key="lm-studio")

        # Initialize history with system prompt
        self.messages = [
            {"role": "system", "content": self.system_prompt}
        ]

    def ensure_model_loaded(self) -> bool:
        """
        Checks if the configured model is loaded in LM Studio and loads it if necessary.
        Returns True if the model is ready, False otherwise.
        """
        model_key = self.model_name
        print(f"[LLM] Checking status for model: {model_key}")
        
        try:
            # 1. Check if model exists and if it's already loaded
            response = requests.get(f"{self.mgmt_url}/models")
            if response.status_code != 200:
                print(f"[LLM] Error: Could not reach LM Studio Management API at {self.mgmt_url}")
                return False
                
            models = response.json().get("models", [])
            target_model = next((m for m in models if m["key"] == model_key), None)
            
            if not target_model:
                available_keys = [m.get("key") for m in models]
                print(f"[LLM] Error: Model '{model_key}' not found. Available keys: {available_keys}")
                return False
                
            if target_model.get("loaded_instances"):
                print(f"[LLM] Model '{model_key}' is already loaded.")
                return True
                
            # 2. Load the model
            print(f"[LLM] Model found but not loaded. Attempting to load with GPU={self.gpu_offload}...")
            payload = {
                "model": model_key
            }
            load_response = requests.post(f"{self.mgmt_url}/models/load", json=payload)
            
            if load_response.status_code == 200:
                print(f"[LLM] Successfully triggered loading for '{model_key}'.")
                return True
            else:
                print(f"[LLM] Error while loading model: {load_response.status_code} - {load_response.text}")
                return False
                
        except Exception as e:
            print(f"[LLM] Connection error to Management API: {e}")
            return False

    def generate_response(self, user_text: str) -> str:
        """Sends a query to the LLM and returns the text response, keeping history."""
        # Ensure the model is loaded before every request
        if not self.ensure_model_loaded():
            return f"konnte das konfigurierte KI-Modell {self.model_name} in LM Studio nicht laden"

        try:
            # Append new user message to history
            self.messages.append({"role": "user", "content": user_text})
            
            # Loop max 5 times to resolve all tool sequences
            for i in range(5):
                # Prepare arguments for the API call
                api_kwargs = {
                    "model": self.model_name,
                    "messages": self.messages,
                    "temperature": 0.7
                }
                
                # Only add tools if schema and executor are provided
                if self.tools_schema and self.tool_executor:
                    api_kwargs["tools"] = self.tools_schema

                response = self.client.chat.completions.create(**api_kwargs)
                response_message = response.choices[0].message
                
                # Check if model wants to call tools
                if response_message.tool_calls and self.tool_executor:
                    # Append the assistant message with tool_calls back to history
                    self.messages.append(response_message)
                    
                    for tool_call in response_message.tool_calls:
                        func_name = tool_call.function.name
                        print(f"[LLM] Trying to execute tool: {func_name}")
                        try:
                            # OpenAI gives arguments as a JSON string
                            args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            args = {}
                            
                        # Execute the injected Python function
                        func_result = self.tool_executor(func_name, args)
                        print(f"[LLM] Tool '{func_name}' result: {func_result}")
                        
                        # Add tool result to conversation history
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": func_name,
                            "content": func_result
                        })
                    
                    # Continue the loop and query LLM again with tool results
                    continue
                else:
                    # Final text response
                    content = response_message.content
                    if content:
                        # Save assistant response to history
                        self.messages.append({"role": "assistant", "content": content})
                        return content
                    return "Keine Antwort von LM Studio"
                    
            return "Fehler: Die maximale Anzahl an Tool-Aufrufen wurde ueberschritten."
        except Exception as e:
            error_msg = f"[LLM] Error generating response: {e}"
            print(error_msg)
            return f"Entschuldigung Boss, ich habe gerade Verbindungsprobleme mit meinem Gehirn-Modul: {e}"
