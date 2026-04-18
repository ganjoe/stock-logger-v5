import os
import json
from py_cli.controller import CLIController, CLIMode
from .llm_service import LLMService
from .prompts import get_tool_definitions
from .logger import log_event

class PTABridge:
    """
    Orchestrates the conversation between the user, the LLM, and the CLI.
    Uses the standalone LLMService for communication and memory.
    """
    def __init__(self, cli_controller: CLIController, config_path: str = None):
        self.cli = cli_controller
        
        # Default to llm_config.json in the same directory as this file
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "llm_config.json")
        
        self.config_path = config_path
        
        # Load configuration
        config = self._load_config()
        if not config:
            self.pta = None
            print(f"[!] Critical Error: LLM config not found at {config_path}")
            return

        # Initialize the new Standalone LLMService
        self.pta = LLMService(
            base_url=config.get("llm_base_url"),
            model_name=config.get("llm_model_name"),
            system_prompt=config.get("system_prompt", ""),
            gpu_offload=config.get("llm_gpu_offload", "max"),
            tools_schema=get_tool_definitions(),
            tool_executor=self._llm_tool_dispatcher
        )

    def _load_config(self) -> dict:
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading LLM config: {e}")
            return {}

    def _llm_tool_dispatcher(self, tool_name: str, args: dict) -> str:
        """
        Adapter that connects the LLM's tool-calls to the CLI execution.
        """
        log_event("PTA_THOUGHT", f"Calling Tool: {tool_name} with args: {args}")
        
        if tool_name == "execute_cli_command":
            cmd = args.get("command")
            if not cmd:
                return "Error: No command provided."

            # LOG: System Execution
            log_event("SYSTEM_EXEC", cmd)
            print(f"  [PTA] Executing CLI: {cmd}")
            
            # Force BOT mode to get clean JSON/Text output
            original_mode = self.cli.context.mode
            self.cli.context.mode = CLIMode.BOT
            try:
                cli_resp = self.cli.process_input(cmd)
            except Exception as e:
                cli_resp = f"Error during execution: {e}"
            finally:
                self.cli.context.mode = original_mode
            
            # LOG: System Result
            log_event("SYSTEM_RESULT", str(cli_resp))
            return str(cli_resp)
        
        return f"Error: Tool '{tool_name}' is not recognized."

    def handle_hub_message(self, msg: dict) -> tuple[str, str]:
        """
        Entry point for Hub messages. 
        Returns (recipient, response_text).
        """
        sender = msg.get("from", "unknown")
        data = msg.get("data", {})
        
        # Extract text from hub data format {"text": "..."}
        if isinstance(data, dict):
            user_input = data.get("text", str(data))
        else:
            user_input = str(data)

        response_text = self.chat(user_input)
        return sender, response_text

    def chat(self, user_input: str) -> str:
        if not self.pta:
            return "❌ LLM Konfiguration fehlt oder Fehler beim Laden von 'secrets/llm_config.json'."

        try:
            # LOG: Initial User Input
            log_event("USER", user_input)

            # Generate response (LLMService handles the history and tool-loops internally)
            final_text = self.pta.generate_response(user_input)
            
            log_event("PTA_RESPONSE", final_text)
            return final_text

        except Exception as e:
            import traceback
            traceback.print_exc()
            err_msg = f"❌ Fehler in der PTA-Kommunikation: {str(e)}"
            log_event("ERROR", err_msg)
            return err_msg
