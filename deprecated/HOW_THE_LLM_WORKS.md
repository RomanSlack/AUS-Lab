# How the LLM Works in AUS-Lab

## Overview

The agentic system uses **Google Gemini** to translate natural language commands into structured drone actions. It appears "smart" because of **constrained output**, **detailed instructions**, and **real-time context**.

## Architecture

```
User Command
    ↓
System Prompt + Current State + User Input
    ↓
Gemini API (gemini-2.0-flash-exp)
    ↓
JSON MissionPlan
    ↓
Pydantic Validation
    ↓
SimulationAPIClient
    ↓
Drone Actions
```

## The Secret: 3 Key Techniques

### 1. Detailed System Prompt
**Location:** `agentic/translation_schema.py:178-238`

The LLM receives comprehensive instructions including:

- **Action Templates**: Complete JSON schemas for all 8 action types
- **Parameter Constraints**: Exact ranges (altitude: 0.1-5.0m, positions: ±10m)
- **10 Explicit Rules**: "Always takeoff before movement", "Use 'all' for swarm-wide"
- **Concrete Examples**: Shows exact input → output transformations

```python
LLM_SYSTEM_PROMPT = """
You are an expert UAV swarm controller...

Available Actions:
{action_templates}  # Injected with full JSON schemas

Rules:
1. Break complex commands into sequential actions
2. Use "all" for swarm-wide actions
...
10. Keep positions within ±10 meters (x, y)

Example Input: "Take off to 2 meters then form a circle"
Example Output: {...complete JSON...}
"""
```

### 2. Structured Output with Pydantic
**Location:** `agentic/translation_schema.py:10-62`

The LLM must output valid JSON matching strict schemas:

```python
class DroneAction(BaseModel):
    action_type: Literal["takeoff", "land", "hover", "goto", "velocity", "formation"]
    drone_ids: Union[List[int], Literal["all"]]
    parameters: Dict[str, Any]
    priority: Literal["high", "medium", "low"]
    wait_for_completion: bool
    expected_duration: Optional[float]

class MissionPlan(BaseModel):
    mission_name: str
    actions: List[DroneAction]
    success_criteria: Optional[str]
    abort_conditions: Optional[List[str]]
```

**Benefits:**
- ✅ Type safety (no hallucinated fields)
- ✅ Immediate validation (Pydantic catches errors)
- ✅ Consistency (same structure every time)

### 3. Real-Time Context Injection
**Location:** `agentic/agentic_controller.py:136-158`

Every command includes current simulation state:

```python
def _generate_plan(self, user_command: str, current_state: Optional[Dict]):
    state_context = f"\nCurrent Swarm State:\n{self.env_translator.state_to_text(current_state)}\n"

    full_prompt = f"""{self.system_prompt}
{state_context}
User Command: "{user_command}"
Generate a MissionPlan in valid JSON format:"""

    response = self.model.generate_content(full_prompt)
```

**Example context sent to LLM:**
```
Current Simulation Time: 15.3s
Number of Drones: 12

Drone 0: Position (0.12, -0.05, 1.50)m, Velocity (0.01, 0.02, 0.00)m/s, Battery 98.5%, Status: ✓
Drone 1: Position (-0.05, 0.15, 0.10)m, Velocity (0.00, 0.01, 0.00)m/s, Battery 100.0%, Status: ✓
...

User Command: "Form a circle at altitude 2m"
```

## The 5-Step Execution Pipeline

**Location:** `agentic/agentic_controller.py:74-133`

```
Step 1: Fetch current state
  GET /state → {drones: [...], timestamp: 15.3}

Step 2: Generate plan with LLM
  Gemini(system_prompt + state + command) → JSON

Step 3: Parse & validate
  Pydantic validates JSON → MissionPlan object

Step 4: Execute actions
  SimulationAPIClient.execute_mission() → API calls

Step 5: Get final state & feedback
  GET /state → final positions, batteries
```

## Action Templates: The Core Magic

**Location:** `agentic/translation_schema.py:65-174`

### The 8 Action Types

| Action Type | Description | Key Parameters | Use Case |
|-------------|-------------|----------------|----------|
| `takeoff` | Make drones ascend to specified altitude | `altitude` (0.1-5.0m) | Initial launch, altitude changes |
| `land` | Descend and land at current position | None | Mission end, battery saving |
| `hover` | Hold current position in air | None | Pause, waiting, observation |
| `goto` | Move single drone to 3D position | `id`, `x`, `y`, `z`, `yaw` (optional) | Individual positioning |
| `velocity` | Direct velocity control (advanced) | `id`, `vx`, `vy`, `vz`, `yaw_rate` | Advanced maneuvers, racing |
| `formation` | Arrange swarm in geometric pattern | `pattern`, `center`, `radius`/`spacing`, `axis` | Coordinated swarm displays |
| `spawn` | Respawn swarm with N drones | `num_drones` (1-50) | Reset, swarm size changes |
| `reset` | Reset entire simulation | None | Full system restart |

**Formation Patterns:**
- `circle` - Drones arranged in circular pattern (requires `radius`)
- `line` - Linear arrangement along axis (requires `spacing`, `axis`)
- `grid` - Square grid layout (requires `spacing`)
- `v` - V-formation like flying geese (requires `spacing`)

Each action has complete specification:

```python
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

    "formation": {
        "description": "Arrange swarm in geometric formation",
        "parameters": {
            "pattern": {"type": "string", "options": ["circle", "line", "grid", "v"]},
            "center": {"type": "array", "length": 3, "description": "[x, y, z]"},
            "radius": {"type": "float", "range": [0.5, 5.0], "unit": "meters"},
            ...
        },
        "examples": [...]
    }
}
```

This dictionary is **JSON-serialized and injected** into the system prompt at runtime:

```python
# agentic_controller.py:44-46
templates_json = json.dumps(ACTION_TEMPLATES, indent=2)
self.system_prompt = LLM_SYSTEM_PROMPT.format(action_templates=templates_json)
```

## Example: Command Processing

**User Input:**
```
"Take off to 2 meters then form a circle"
```

**LLM Receives:**
```
System Prompt: You are an expert UAV swarm controller...
Available Actions: {takeoff: {...}, formation: {...}, ...}
Rules: 1. Break complex commands... 10. Keep positions within ±10m

Current Swarm State:
Drone 0: Position (0.00, 0.00, 0.10)m, Battery 100%, Status: ✓
...

User Command: "Take off to 2 meters then form a circle"
```

**LLM Outputs:**
```json
{
  "mission_name": "Takeoff and circle formation",
  "actions": [
    {
      "action_type": "takeoff",
      "drone_ids": "all",
      "parameters": {"altitude": 2.0},
      "priority": "high",
      "wait_for_completion": true,
      "expected_duration": 5.0
    },
    {
      "action_type": "formation",
      "drone_ids": "all",
      "parameters": {
        "pattern": "circle",
        "center": [0, 0, 2.0],
        "radius": 2.0
      },
      "priority": "medium",
      "wait_for_completion": true,
      "expected_duration": 8.0
    }
  ]
}
```

**System Executes:**
```
POST /takeoff {"ids": ["all"], "altitude": 2.0}
→ Wait 5 seconds
POST /formation {"pattern": "circle", "center": [0, 0, 2.0], "radius": 2.0}
→ Wait 8 seconds
```

## Why It Works So Well

1. **Constrained Output Space**
   - Only 8 possible action types
   - All parameters have explicit ranges
   - No room for hallucination

2. **Perfect Examples**
   - System prompt includes complete input→output examples
   - LLM just pattern-matches and fills templates

3. **JSON Extraction Robustness**
   ```python
   # Handles markdown code blocks automatically
   if "```json" in text:
       text = text.split("```json")[1].split("```")[0]
   ```

4. **Immediate Validation**
   - Pydantic catches type errors instantly
   - Invalid plans never reach execution

5. **Real-Time Awareness**
   - LLM sees current positions, batteries, status
   - Can make context-aware decisions

## Technical Details

**Model:** `gemini-2.0-flash-exp` (Google Gemini Flash)
- Fast inference (~1-2s per command)
- Excellent JSON adherence
- Strong pattern matching

**API Key:** Loaded from `.env` file
```bash
GEMINI_API_KEY=your_key_here
```

**Libraries:**
- `google-generativeai>=0.3.0` - Gemini API client
- `pydantic>=2.0.0` - Schema validation
- `python-dotenv>=1.0.0` - Environment management

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `agentic/translation_schema.py` | System prompt + action templates | 239 |
| `agentic/agentic_controller.py` | Main LLM controller logic | 303 |
| `agentic/api_translator.py` | API client + state translator | 279 |

## TL;DR

The LLM appears "smart" because it's a **sophisticated template-filler** with:
- Detailed instructions (system prompt)
- Perfect examples (action templates)
- Real-time context (current state)
- Strict validation (Pydantic schemas)
- Constrained outputs (no creativity needed)

It doesn't "understand" drones—it matches patterns and fills JSON schemas. The magic is in the **engineering**, not the model! 🎯
