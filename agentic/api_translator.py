"""
API Translator: Converts structured drone actions to simulation API calls.
"""

import requests
import time
from typing import Dict, List, Optional, Any
from translation_schema import DroneAction, MissionPlan


class SimulationAPIClient:
    """Client for interacting with the AUS-Lab simulation API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.timeout = 5.0

    def health_check(self) -> bool:
        """Check if simulation API is available."""
        try:
            response = requests.get(f"{self.base_url}/", timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            print(f"[API] Health check failed: {e}")
            return False

    def get_state(self) -> Optional[Dict[str, Any]]:
        """Get current state of all drones."""
        try:
            response = requests.get(f"{self.base_url}/state", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[API] Failed to get state: {e}")
            return None

    def execute_action(self, action: DroneAction) -> Dict[str, Any]:
        """
        Execute a single drone action by calling appropriate API endpoint.

        Returns:
            Response dict with 'success', 'message', and 'data' fields
        """
        print(f"\n[API] Executing: {action.action_type} for drones {action.drone_ids}")
        print(f"[API] Parameters: {action.parameters}")

        try:
            # Map action type to endpoint and prepare request
            endpoint, payload = self._map_action_to_request(action)

            # Execute API call
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            print(f"[API] ✓ Success: {result.get('message', 'OK')}")

            return {
                "success": True,
                "message": result.get('message', 'Action completed'),
                "data": result
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            print(f"[API] ✗ Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "data": None
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"[API] ✗ Error: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "data": None
            }

    def _map_action_to_request(self, action: DroneAction) -> tuple[str, Dict]:
        """
        Map DroneAction to API endpoint and request payload.

        Returns:
            (endpoint_path, payload_dict)
        """
        action_type = action.action_type
        params = action.parameters
        ids = action.drone_ids

        # Convert drone_ids to proper format
        if ids == "all":
            ids_list = ["all"]
        elif isinstance(ids, list):
            ids_list = ids
        else:
            ids_list = [ids]

        # Map to API endpoints
        if action_type == "takeoff":
            return "/takeoff", {
                "ids": ids_list,
                "altitude": params.get("altitude", 1.5)
            }

        elif action_type == "land":
            return "/land", {
                "ids": ids_list
            }

        elif action_type == "hover":
            return "/hover", {
                "ids": ids_list
            }

        elif action_type == "goto":
            return "/goto", {
                "id": params.get("id", 0),
                "x": params.get("x", 0.0),
                "y": params.get("y", 0.0),
                "z": params.get("z", 1.0),
                "yaw": params.get("yaw", 0.0)
            }

        elif action_type == "velocity":
            return "/velocity", {
                "id": params.get("id", 0),
                "vx": params.get("vx", 0.0),
                "vy": params.get("vy", 0.0),
                "vz": params.get("vz", 0.0),
                "yaw_rate": params.get("yaw_rate", 0.0)
            }

        elif action_type == "formation":
            return "/formation", {
                "pattern": params.get("pattern", "circle"),
                "center": params.get("center", [0.0, 0.0, 1.5]),
                "spacing": params.get("spacing", 1.0),
                "radius": params.get("radius", 1.5),
                "axis": params.get("axis", "x")
            }

        elif action_type == "spawn":
            return "/spawn", {
                "num": params.get("num", 5)
            }

        elif action_type == "reset":
            return "/reset", {}

        else:
            raise ValueError(f"Unknown action type: {action_type}")

    def execute_mission(self, mission: MissionPlan, feedback_callback=None) -> Dict[str, Any]:
        """
        Execute a complete mission plan.

        Args:
            mission: MissionPlan with ordered actions
            feedback_callback: Optional function(action, result, state) called after each action

        Returns:
            Dict with mission results and execution summary
        """
        print(f"\n{'='*60}")
        print(f"[MISSION] Starting: {mission.mission_name}")
        print(f"[MISSION] Total actions: {len(mission.actions)}")
        print(f"{'='*60}\n")

        results = []
        successful_actions = 0
        start_time = time.time()

        for idx, action in enumerate(mission.actions, 1):
            print(f"\n[MISSION] Step {idx}/{len(mission.actions)}")

            # Execute action
            result = self.execute_action(action)
            results.append({
                "action": action.dict(),
                "result": result,
                "timestamp": time.time() - start_time
            })

            if not result["success"]:
                print(f"[MISSION] ✗ Action failed, checking abort conditions...")
                if mission.abort_conditions:
                    print(f"[MISSION] Aborting mission due to failure")
                    break
            else:
                successful_actions += 1

            # Wait for completion if specified
            if action.wait_for_completion and action.expected_duration:
                print(f"[MISSION] Waiting {action.expected_duration}s for completion...")
                time.sleep(action.expected_duration)

            # Get current state for feedback
            if feedback_callback:
                state = self.get_state()
                feedback_callback(action, result, state)

            # Small delay between actions
            time.sleep(0.5)

        total_time = time.time() - start_time
        success_rate = successful_actions / len(mission.actions) * 100

        print(f"\n{'='*60}")
        print(f"[MISSION] Complete: {mission.mission_name}")
        print(f"[MISSION] Success Rate: {success_rate:.1f}% ({successful_actions}/{len(mission.actions)})")
        print(f"[MISSION] Total Time: {total_time:.2f}s")
        print(f"{'='*60}\n")

        return {
            "mission_name": mission.mission_name,
            "total_actions": len(mission.actions),
            "successful_actions": successful_actions,
            "success_rate": success_rate,
            "total_time": total_time,
            "results": results,
            "final_state": self.get_state()
        }


class EnvironmentTranslator:
    """Translates simulation state into natural language for LLM feedback."""

    @staticmethod
    def state_to_text(state: Dict[str, Any]) -> str:
        """Convert drone state dictionary to natural language description."""
        if not state or "drones" not in state:
            return "No state information available."

        drones = state["drones"]
        timestamp = state.get("timestamp", 0)

        lines = [
            f"Current Simulation Time: {timestamp:.1f}s",
            f"Number of Drones: {len(drones)}",
            ""
        ]

        for drone in drones:
            pos = drone["pos"]
            vel = drone["vel"]
            lines.append(
                f"Drone {drone['id']}: "
                f"Position ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})m, "
                f"Velocity ({vel[0]:.2f}, {vel[1]:.2f}, {vel[2]:.2f})m/s, "
                f"Battery {drone['battery']:.1f}%, "
                f"Status: {'✓ Healthy' if drone['healthy'] else '✗ Unhealthy'}"
            )

        return "\n".join(lines)

    @staticmethod
    def state_to_summary(state: Dict[str, Any]) -> str:
        """Generate a brief summary of swarm state."""
        if not state or "drones" not in state:
            return "No drones active."

        drones = state["drones"]
        avg_altitude = sum(d["pos"][2] for d in drones) / len(drones)
        avg_battery = sum(d["battery"] for d in drones) / len(drones)
        healthy_count = sum(1 for d in drones if d["healthy"])

        return (
            f"{len(drones)} drones active, "
            f"avg altitude {avg_altitude:.2f}m, "
            f"avg battery {avg_battery:.1f}%, "
            f"{healthy_count}/{len(drones)} healthy"
        )
