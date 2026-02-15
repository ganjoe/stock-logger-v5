import google.generativeai as genai
from py_cli.controller import CLIController, CLIMode
from .client import GeminiPTA
from .prompts import SYSTEM_INSTRUCTION, get_tool_definitions

class PTABridge:
    """
    Orchestrates the conversation between the user, Gemini, and the CLI.
    """
    def __init__(self, cli_controller: CLIController):
        self.cli = cli_controller
        self.pta = GeminiPTA()
        self.chat_history = []
        
        # Initialize with system instruction if supported by the client implementation
        # For simplicity in this bridge, we can just prepend it or use the model's system_instruction param
        # if we modify GeminiPTA. For now, let's assume we pass it in the first message or as a role.
        if self.pta.is_configured():
            # In Gemini 1.5, we can pass system_instruction to the constructor.
            # Updated GeminiPTA to support this if needed.
            pass

    def chat(self, user_input: str) -> str:
        if not self.pta.is_configured():
            return "❌ Gemini API Key fehlt. Bitte erstelle 'secrets/gemini_config.json' mit deinem API-Key."

        try:
            tools = get_tool_definitions()
            # 1. Start or resume chat
            if not self.chat_history:
                # Setup with system instructions as user/model prelude
                self.chat_history.append({"role": "user", "parts": [SYSTEM_INSTRUCTION]})
                self.chat_history.append({"role": "model", "parts": ["Verstanden. Ich bin bereit."] })

            chat = self.pta.model.start_chat(history=self.chat_history)
            
            # Token counting for prompt
            prompt_tokens = self.pta.count_tokens(user_input)
            print(f"  [PTA] Prompt Tokens: {prompt_tokens}")
            
            response = chat.send_message(user_input, tools=tools)
            
            # 2. Loop while model wants to call tools
            while response.candidates[0].content.parts[0].function_call:
                fc = response.candidates[0].content.parts[0].function_call
                if fc.name == "execute_cli_command":
                    cmd = fc.args["command"]
                    print(f"  [PTA] Executing CLI: {cmd}")
                    
                    # Force BOT mode to get JSON output
                    original_mode = self.cli.context.mode
                    self.cli.context.mode = CLIMode.BOT
                    cli_resp = self.cli.process_input(cmd)
                    self.cli.context.mode = original_mode
                    
                    # Send function response back to the chat
                    # We must pass the response to the same conversation
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
                    break

            # 3. Synchronize history
            self.chat_history = chat.history
            
            # Token counting for response
            resp_tokens = self.pta.count_tokens(response.candidates[0].content)
            print(f"  [PTA] Response Tokens: {resp_tokens}")
            
            # 4. Final Text Response
            return response.text

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"❌ Fehler in der PTA-Kommunikation: {str(e)}"
