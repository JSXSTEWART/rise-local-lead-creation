import google.generativeai as genai
import os

# Get API key
api_key = os.getenv("GOOGLE_GEMINI_API_KEY", "REDACTED")
print(f"Using API key: {api_key[:20]}...{api_key[-10:]}")

# Configure Gemini
genai.configure(api_key=api_key)

# List all available models
print("\nAvailable Gemini models:")
print("=" * 60)

try:
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"\n✓ {model.name}")
            print(f"  Display name: {model.display_name}")
            print(f"  Methods: {model.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")
