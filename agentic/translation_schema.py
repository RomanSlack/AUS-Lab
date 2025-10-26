"""
Translation Schema for LLM → Simulation API
Defines the structured format for converting LLM intentions to API calls.
"""

from typing import Literal, List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field


class DroneAction(BaseModel):
    """Base schema for a single drone action that maps to API endpoints."""

    action_type: Literal[
        "takeoff", "land", "hover", "goto", "velocity",
        "formation", "spawn", "reset"
    ] = Field(description="Type of action to perform")

    drone_ids: Union[List[int], Literal["all"]] = Field(
        default="all",
        description="Target drone IDs or 'all' for entire swarm"
    )

    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters"
    )

    priority: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="Execution priority for multi-step plans"
    )

    wait_for_completion: bool = Field(
        default=True,
        description="Whether to wait for this action to complete before next"
    )

    expected_duration: Optional[float] = Field(
        default=None,
        description="Expected time in seconds for action completion"
    )


class MissionPlan(BaseModel):
    """Complete mission plan with multiple actions."""

    mission_name: str = Field(description="Human-readable mission description")

    actions: List[DroneAction] = Field(
        description="Ordered list of actions to execute"
    )

    success_criteria: Optional[str] = Field(
        default=None,
        description="Conditions that define mission success"
    )

    abort_conditions: Optional[List[str]] = Field(
        default=None,
        description="Conditions that should abort the mission"
    )


# Action Templates for LLM to use
ACTION_TEMPLATES = {
    "takeoff": {
        "description": "Make drones take off to specified altitude",
        "parameters": {
            "altitude": {"type": "float", "range": [0.1, 5.0], "unit": "meters"}
        },
        "example": {
            "action_type": "takeoff",
            "drone_ids": "all",
            "parameters": {"altitude": 1.5}
        }
    },

    "land": {
        "description": "Land drones at current position",
        "parameters": {},
        "example": {
            "action_type": "land",
            "drone_ids": "all",
            "parameters": {}
        }
    },

    "goto": {
        "description": "Move a single drone to target position",
        "parameters": {
            "id": {"type": "int", "description": "Drone ID"},
            "x": {"type": "float", "range": [-10, 10], "unit": "meters"},
            "y": {"type": "float", "range": [-10, 10], "unit": "meters"},
            "z": {"type": "float", "range": [0.1, 5.0], "unit": "meters"},
            "yaw": {"type": "float", "range": [-3.14, 3.14], "unit": "radians", "optional": True}
        },
        "example": {
            "action_type": "goto",
            "drone_ids": [0],
            "parameters": {"id": 0, "x": 2.0, "y": 1.0, "z": 1.5, "yaw": 0.0}
        }
    },

    "formation": {
        "description": "Arrange swarm in geometric formation",
        "parameters": {
            "pattern": {
                "type": "string",
                "options": ["circle", "line", "grid", "v"],
                "description": "Formation pattern"
            },
            "center": {
                "type": "array",
                "length": 3,
                "description": "[x, y, z] center point"
            },
            "spacing": {
                "type": "float",
                "range": [0.5, 3.0],
                "unit": "meters",
                "description": "Distance between drones (for line/grid/v)"
            },
            "radius": {
                "type": "float",
                "range": [0.5, 5.0],
                "unit": "meters",
                "description": "Circle radius (for circle only)"
            },
            "axis": {
                "type": "string",
                "options": ["x", "y"],
                "description": "Line direction (for line only)"
            }
        },
        "examples": [
            {
                "action_type": "formation",
                "drone_ids": "all",
                "parameters": {"pattern": "circle", "center": [0, 0, 2.0], "radius": 2.0}
            },
            {
                "action_type": "formation",
                "drone_ids": "all",
                "parameters": {"pattern": "line", "center": [0, 0, 1.5], "spacing": 1.0, "axis": "x"}
            }
        ]
    },

    "hover": {
        "description": "Hold current position",
        "parameters": {},
        "example": {
            "action_type": "hover",
            "drone_ids": "all",
            "parameters": {}
        }
    },

    "velocity": {
        "description": "Set drone velocity directly (advanced)",
        "parameters": {
            "id": {"type": "int", "description": "Drone ID"},
            "vx": {"type": "float", "range": [-5, 5], "unit": "m/s"},
            "vy": {"type": "float", "range": [-5, 5], "unit": "m/s"},
            "vz": {"type": "float", "range": [-5, 5], "unit": "m/s"},
            "yaw_rate": {"type": "float", "range": [-6.28, 6.28], "unit": "rad/s", "optional": True}
        },
        "example": {
            "action_type": "velocity",
            "drone_ids": [0],
            "parameters": {"id": 0, "vx": 1.0, "vy": 0.0, "vz": 0.0, "yaw_rate": 0.0}
        }
    }
}


# System prompt template for LLM
LLM_SYSTEM_PROMPT = """
You are an expert UAV swarm controller. Your task is to translate natural language commands
into structured drone actions using the provided JSON schema.

Available Actions:
{action_templates}

Output Format:
Always respond with valid JSON matching the MissionPlan schema:
{{
  "mission_name": "Brief description of the mission",
  "actions": [
    {{
      "action_type": "takeoff|land|hover|goto|velocity|formation",
      "drone_ids": "all" or [0, 1, 2],
      "parameters": {{}},
      "priority": "high|medium|low",
      "wait_for_completion": true|false,
      "expected_duration": 5.0
    }}
  ],
  "success_criteria": "Optional success condition",
  "abort_conditions": ["Optional abort conditions"]
}}

Rules:
1. Break complex commands into sequential actions
2. Use "all" for swarm-wide actions
3. Use specific IDs for individual drone control
4. Set expected_duration based on distance/altitude changes
5. Set wait_for_completion=true for actions that must complete before next
6. Always include takeoff before any movement if drones are grounded
7. Use formation for coordinated swarm patterns
8. Use goto for individual drone positioning
9. Keep altitude between 0.1 and 5.0 meters
10. Keep positions within ±10 meters (x, y)

Example Input: "Take off to 2 meters then form a circle"
Example Output:
{{
  "mission_name": "Takeoff and circle formation",
  "actions": [
    {{
      "action_type": "takeoff",
      "drone_ids": "all",
      "parameters": {{"altitude": 2.0}},
      "priority": "high",
      "wait_for_completion": true,
      "expected_duration": 5.0
    }},
    {{
      "action_type": "formation",
      "drone_ids": "all",
      "parameters": {{"pattern": "circle", "center": [0, 0, 2.0], "radius": 2.0}},
      "priority": "medium",
      "wait_for_completion": true,
      "expected_duration": 8.0
    }}
  ]
}}
"""
