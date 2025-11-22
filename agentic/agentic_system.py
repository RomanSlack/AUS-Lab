import json
import google.generativeai as genai
from jsonschema import validate, ValidationError
from hive_mind import HiveMindController

# Configure Gemini API - This will be done by run_agentic_system.py
# genai.configure(api_key="YOUR_API_KEY")

# JSON Schema for the individual drone plan
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

# JSON Schema for the hive mind plan
hive_mind_plan_schema = {
    "type": "object",
    "properties": {
        "task": {"type": "string"},
        "area": {"type": "string"},
        "swarm": {
            "type": "object",
            "properties": {
                "formation": {"type": "string"},
                "behavior": {"type": "string"}
            },
            "required": ["formation", "behavior"]
        },
        "priority": {
            "type": "string",
            "enum": ["high", "medium", "low"]
        }
    },
    "required": ["task", "area", "swarm", "priority"]
}

def agentic_system(user_command: str, hive_mind_enabled: bool = False) -> dict:
    """
    Takes a natural language command and returns structured drone instructions.
    """
    if hive_mind_enabled:
        prompt = f"""
        You are controlling a swarm of drones as a single entity (hive mind).
        Instruction: {user_command}
        Output the plan in JSON with fields:
        - task (string)
        - area (string or coordinates)
        - swarm (object with formation and behavior)
        - priority (high/medium/low)
        """
        schema = hive_mind_plan_schema
    else:
        prompt = f"""
        You are controlling a swarm of drones.
        Instruction: {user_command}
        Output the plan in JSON with fields:
        - task (string)
        - area (string or coordinates)
        - drones (list of drone IDs or roles, it MUST be a list)
        - priority (high/medium/low)
        """
        schema = plan_schema

    response = genai.GenerativeModel("gemini-2.5-flash").generate_content(prompt)
    
    try:
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        plan = json.loads(text)
        validate(instance=plan, schema=schema)
    except json.JSONDecodeError:
        plan = {"error": "Could not parse response", "raw": response.text}
    except ValidationError as e:
        plan = {"error": "JSON schema validation failed", "details": str(e), "raw": response.text}
    
    if hive_mind_enabled and "error" not in plan:
        controller = HiveMindController(plan)
        controller.execute()

    return plan

# Example usage
if __name__ == "__main__":
    command = "Survey the north side of the map and report unusual activity."
    
    # Example with individual drone control
    plan = agentic_system(command)
    print("Structured Plan (Individual):", plan)

    # Example with hive mind control
    hive_mind_plan = agentic_system(command, hive_mind_enabled=True)
    print("Structured Plan (Hive Mind):", hive_mind_plan)
    # This plan can now be sent to the simulation API layer
