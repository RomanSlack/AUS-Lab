# AUS-Lab
Research the connection between Swarm Structures, HIL, Agentic Systems, LLMs

import json
import google.generativeai as genai  # Gemini API client

# Configure Gemini API
genai.configure(api_key="YOUR_API_KEY")

def agentic_system(user_command: str) -> dict:
    """
    Takes a natural language command and returns structured drone instructions.
    """
    prompt = f"""
    You are controlling a swarm of drones.
    Instruction: {user_command}
    Output the plan in JSON with fields:
    - task (string)
    - area (string or coordinates)
    - drones (list of drone IDs or roles)
    - priority (high/medium/low)
    """

    response = genai.GenerativeModel("gemini-pro").generate_content(prompt)
    
    # Try to parse JSON from the model's response
    try:
        plan = json.loads(response.text)
    except Exception:
        plan = {"error": "Could not parse response", "raw": response.text}
    
    return plan


# Example usage
if __name__ == "__main__":
    command = "Survey the north side of the map and report unusual activity."
    plan = agentic_system(command)
    print("Structured Plan:", plan)

    # This plan can now be sent to the simulation API layer