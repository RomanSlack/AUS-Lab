
import requests
import json
import time

class SwarmState:
    """
    Manages the collective state of the swarm.
    This includes drone positions, statuses, and other sensor data.
    """
    def __init__(self, num_drones):
        self.drones = {i: {"position": [0, 0, 0], "status": "idle"} for i in range(num_drones)}

    def update_drone_state(self, drone_id, position, status):
        """Updates the state of a specific drone."""
        if drone_id in self.drones:
            self.drones[drone_id]["position"] = position
            self.drones[drone_id]["status"] = status
        else:
            print(f"Warning: Drone ID {drone_id} not found in swarm state.")

    def get_swarm_state(self):
        """Returns the current state of the entire swarm."""
        return self.drones

    def get_drone_state(self, drone_id):
        """Returns the state of a specific drone."""
        return self.drones.get(drone_id, None)

class HiveMindController:
    """
    The central brain of the swarm, directing its overall behavior.
    """
    def __init__(self, plan, num_drones=4, leader_id=0, api_url="http://localhost:8000"):
        self.plan = plan
        self.num_drones = num_drones
        self.leader_id = leader_id
        self.api_url = api_url
        self.swarm_state = SwarmState(num_drones)
        self.formation = self.plan["swarm"]["formation"]
        self.behavior = self.plan["swarm"]["behavior"]

    def start(self):
        """
        Waits for the simulation to be ready and then sends the initial command.
        """
        self.wait_for_simulation()
        # Send initial formation command
        initial_center = self._get_area_center()
        self._send_formation_command(initial_center)
        print("Hive Mind has established connection and sent initial formation command.")

    def wait_for_simulation(self, timeout=30):
        """
        Waits for the simulation API to become available by polling the health endpoint.
        """
        print("Waiting for simulation to become available...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.api_url}/health")
                if response.status_code == 200 and response.json().get("status") == "ready":
                    print("Simulation is ready.")
                    return True
            except requests.exceptions.RequestException:
                # Ignore connection errors and try again
                pass
            time.sleep(1)
        
        print(f"Error: Simulation did not become available within {timeout} seconds.")
        raise RuntimeError("Could not connect to the simulation.")

    def set_formation(self, pattern):
        """
        Sets a new formation pattern for the swarm.
        """
        if pattern not in ["line", "circle"]:
            print(f"Unknown formation: {pattern}. Use 'line' or 'circle'.")
            return
        
        print(f"Setting formation to {pattern}...")
        self.formation = pattern
        # Re-issue the formation command with the last known center
        # For simplicity, we get the last drone's position as an anchor.
        # A more robust solution might use the average position of the swarm.
        last_center = self.swarm_state.get_drone_state(0)["position"]
        self._send_formation_command(last_center)

    def move_center_to(self, center_coords):
        """
        Commands the swarm to move its center to a new location.
        """
        print(f"Moving swarm center to {center_coords}...")
        self._send_formation_command(center_coords)

    def get_and_print_state(self):
        """
        Fetches the latest swarm state and prints it to the console.
        """
        self._update_swarm_state_from_simulation()
        print("\033[H\033[J", end="") # Clear the console
        print("--- Swarm State ---")
        all_states = self.swarm_state.get_swarm_state()
        for drone_id, data in all_states.items():
            pos = data['position']
            pos_str = f"[{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]"
            print(f"  Drone {drone_id}: Position={pos_str}, Status={data['status']}")
        print("---------------------")
        print("Commands: formation <line|circle>, move <x y z>, status, exit")

    def _update_swarm_state_from_simulation(self):
        """
        Fetches the current state of all drones from the simulation API.
        """
        try:
            response = requests.get(f"{self.api_url}/drones")
            response.raise_for_status()
            drones_data = response.json()
            for drone_id, data in drones_data.items():
                self.swarm_state.update_drone_state(int(drone_id), data["position"], data["status"])
        except requests.exceptions.RequestException:
            # Don't print errors here to keep the UI clean
            pass
        except json.JSONDecodeError:
            pass # Keep UI clean


    def _send_formation_command(self, center):
        """
        Sends a formation command to the simulation API.
        """
        formation_payload = {
            "pattern": self.formation,
            "center": center,
            "spacing": 1.0,
            "radius": 2.0,
            "axis": "x"
        }

        try:
            response = requests.post(f"{self.api_url}/formation", json=formation_payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending formation command: {e}")

    def _get_area_center(self):
        """
        Parses the area string and returns the center coordinates.
        For simplicity, we'll assume the area is a string like "10,20,5"
        """
        try:
            coords = [float(c) for c in self.plan["area"].split(',')]
            return coords
        except (ValueError, IndexError):
            return [0, 0, 5]
