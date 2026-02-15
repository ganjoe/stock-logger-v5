import google.generativeai as genai
import json
import os

def list_models():
    config_path = "secrets/gemini_config.json"
    if not os.path.exists(config_path):
        print("Config missing")
        return
    
    with open(config_path, "r") as f:
        config = json.load(f)
        api_key = config.get("api_key")
        
    genai.configure(api_key=api_key)
    for m in genai.list_models():
        print(f"Name: {m.name}, Supported: {m.supported_generation_methods}")

if __name__ == "__main__":
    list_models()
