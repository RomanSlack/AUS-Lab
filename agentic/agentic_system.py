import json
import google.generativeai as genai
from jsonschema import validate, ValidationError

# Configure Gemini API
genai.configure(api_key="YOUR_API_KEY")

# JSON Schema for the plan
plan_schema = {
    "type": "object",
    "properties": {
        "task": {"type": "string"},
        "area": {"type": "string"},
        "drones": {
            "type": "array",
            "items": {"type": "string"}
        },
        "priority": {
            "type": "string",
            "enum": ["high", "medium", "low"]
        }
    },
    "required": ["task", "area", "drones", "priority"]
}

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
    - drones (list of drone IDs or roles, it MUST be a list)
    - priority (high/medium/low)
    """

    response = genai.GenerativeModel("gemini-2.5-flash").generate_content(prompt)
    
    try:
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        plan = json.loads(text)
        validate(instance=plan, schema=plan_schema)
    except json.JSONDecodeError:
        plan = {"error": "Could not parse response", "raw": response.text}
    except ValidationError as e:
        plan = {"error": "JSON schema validation failed", "details": str(e), "raw": response.text}
    
    return plan

# Example usage
if __name__ == "__main__":
    command = "Survey the north side of the map and report unusual activity."
    plan = agentic_system(command)
    print("Structured Plan:", plan)

    # This plan can now be sent to the simulation API layer
