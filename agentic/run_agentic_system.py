
import sys
import os
from dotenv import load_dotenv
import agentic_system

# Load the .env file from the parent directory
load_dotenv(dotenv_path="../.env")

# Configure the Gemini API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in .env file")
    sys.exit(1)

agentic_system.genai.configure(api_key=api_key)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = ' '.join(sys.argv[1:])
    else:
        command = "Survey the north side of the map and report unusual activity."

    plan = agentic_system.agentic_system(command)
    print("Structured Plan:", plan)
