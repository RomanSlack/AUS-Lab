import os
from dotenv import load_dotenv

# Load the .env file from the parent directory (AUS-lab/.env)
load_dotenv(dotenv_path="../.env")

api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    print("✅ API key loaded successfully:", api_key[:5] + "*****")
else:
    print("❌ Could not load API key")