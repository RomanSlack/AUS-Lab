import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load .env
load_dotenv(dotenv_path="../.env")

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# Create a model instance
model = genai.GenerativeModel("gemini-2.5-flash")

# Test a simple prompt
response = model.generate_content("Hello Gemini, can you summarize what UAV swarms are?")
print(response.text)