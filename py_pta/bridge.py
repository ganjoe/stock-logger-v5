import google.generativeai as genai
from py_cli.controller import CLIController, CLIMode
from .client import GeminiPTA
from .prompts import SYSTEM_INSTRUCTION, get_tool_definitions
from .logger import log_event

class PTABridge:
    """
    Orchestrates the conversation between the user, Gemini, and the CLI.
    """
    def __init__(self, cli_controller: CLIController):
        self.cli = cli_controller
        self.pta = GeminiPTA()
        self.chat_history = []
        
        if self.pta.is_configured():
            pass

    def chat(self, user_input: str) -> str:
        if not self.pta.is_configured():
            return "❌ Gemini API Key fehlt. Bitte erstelle 'secrets/gemini_config.json' mit deinem API-Key."

        try:
            # LOG: Initial User Input
            log_event("USER", user_input)

            tools = get_tool_definitions()
            # 1. Start or resume chat
            if not self.chat_history:
                # Setup with system instructions as user/model prelude
                self.chat_history.append({"role": "user", "parts": [SYSTEM_INSTRUCTION]})
                self.chat_history.append({"role": "model", "parts": ["Verstanden. Ich bin bereit."] })

            chat = self.pta.model.start_chat(history=self.chat_history)
            
            # Token counting for prompt
            prompt_tokens = self.pta.count_tokens(user_input)
            # print(f"  [PTA] Prompt Tokens: {prompt_tokens}") # Debugging removed from stdout
            
            response = chat.send_message(user_input, tools=tools)
            
            # 2. Main Loop for Function Calling
            while True:
                # IMPORTANT: We check if ANY part of the current response is a function call
                parts = response.candidates[0].content.parts
                # Find the first function call if any
                fc = next((p.function_call for p in parts if p.function_call), None)
                
                if not fc:
                    # Break when no more tools are requested
                    break
                    
                # LOG: PTA Decision
                log_event("PTA_THOUGHT", f"Calling Function: {fc.name} with args: {fc.args}")
                
                if fc.name == "execute_cli_command":
                    cmd = fc.args["command"]
                    
                    # LOG: System Execution
                    log_event("SYSTEM_EXEC", cmd)
                    print(f"  [PTA] Executing CLI: {cmd}")
                    
                    # Force BOT mode to get JSON output
                    original_mode = self.cli.context.mode
                    self.cli.context.mode = CLIMode.BOT
                    cli_resp = self.cli.process_input(cmd)
                    self.cli.context.mode = original_mode
                    
                    # LOG: System Result
                    log_event("SYSTEM_RESULT", str(cli_resp))
                    
                    # Send function response back to the chat
                    response = chat.send_message(
                        genai.protos.Content(
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name="execute_cli_command",
                                    response={"result": cli_resp}
                                )
                            )]
                        ),
                        tools=tools
                    )
                else:
                    # Generic exit for unknown tools
                    break

            # 3. Synchronize history
            self.chat_history = chat.history
            
            # Token counting for response
            resp_tokens = self.pta.count_tokens(response.candidates[0].content)
            # print(f"  [PTA] Response Tokens: {resp_tokens}") # Debugging removed from stdout
            
            # 4. Final Text Response
            final_text = response.text
            log_event("PTA_RESPONSE", final_text)
            
            return final_text

        except Exception as e:
            import traceback
            traceback.print_exc()
            err_msg = f"❌ Fehler in der PTA-Kommunikation: {str(e)}"
            log_event("ERROR", err_msg)
            return err_msg
