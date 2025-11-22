"""
Main entry point for the AUS-Lab visual simulation.

This script initializes and runs the PyBullet simulation with a GUI,
while also hosting a Flask API server in a background thread to accept
external commands for controlling the drone swarm.
"""

import threading
import time
import argparse # Import argparse
from flask import Flask, jsonify, request

from swarm import SwarmWorld, DroneCommand

# --- Parse Command Line Arguments ---
parser = argparse.ArgumentParser(description="AUS-Lab Swarm Simulation")
parser.add_argument("--num", default=4, type=int, help="Number of drones (default: 4)")
parser.add_argument("--headless", action="store_true", help="Run simulation in headless mode (no GUI)")
args = parser.parse_args()

# --- Global Simulation Instance ---
# This creates a single instance of the SwarmWorld, which will manage
# the PyBullet simulation environment. `gui=True` is essential for visuals.
world = SwarmWorld(gui=not args.headless, num_drones=args.num) # Use parsed arguments


# --- API Server ---
# This Flask app will run in a background thread to avoid blocking the
# simulation loop. It allows external scripts to control the swarm.
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint to confirm the API server is running."""
    return jsonify({"status": "ready", "simulation_time": world.sim_time})

@app.route("/state", methods=["GET"])
def get_state():
    """Returns the full current state of all drones in the swarm."""
    return jsonify(world.get_state())
    
@app.route("/drones", methods=["GET"])
def get_drones_simplified():
    """
    Returns a simplified state compatible with the HiveMindController.
    """
    full_state = world.get_state()
    simplified_state = {}
    for drone_data in full_state.get("drones", []):
        simplified_state[drone_data["id"]] = {
            "position": drone_data["pos"],
            "status": "flying" # Status is more complex in SwarmWorld, so we simplify
        }
    return jsonify(simplified_state)


@app.route("/formation", methods=["POST"])
def set_formation():
    """
    Commands the entire swarm to adopt a specific formation.
    The HiveMindController uses this endpoint.
    """
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    # The SwarmWorld has a thread-safe command queue. We create a
    # command object and enqueue it for processing in the next sim step.
    cmd = DroneCommand(
        cmd_type="formation",
        drone_ids="all",
        params={
            "pattern": data.get("pattern", "line"),
            "center": data.get("center", [0, 0, 1]),
            "spacing": data.get("spacing", 1.0),
            "radius": data.get("radius", 2.0),
            "axis": data.get("axis", "x"),
        }
    )
    world.enqueue_command(cmd)
    return jsonify({"status": "success", "message": f"Formation '{data.get('pattern')}' command enqueued."})

@app.route("/takeoff", methods=["POST"])
def takeoff():
    """Commands all drones to take off."""
    cmd = DroneCommand(cmd_type="takeoff", drone_ids="all", params={"altitude": 1.0})
    world.enqueue_command(cmd)
    return jsonify({"status": "success", "message": "Takeoff command enqueued."})

@app.route("/land", methods=["POST"])
def land():
    """Commands all drones to land."""
    cmd = DroneCommand(cmd_type="land", drone_ids="all", params={})
    world.enqueue_command(cmd)
    return jsonify({"status": "success", "message": "Land command enqueued."})


def run_api_server():
    """Runs the Flask app in a background thread."""
    # Use '0.0.0.0' to make it accessible from other scripts
    app.run(host='0.0.0.0', port=8000, debug=False)


# --- Main Simulation Loop ---
def main():
    """
    Starts the API server and then enters the main simulation loop.
    """
    print("Starting API server in background thread...")
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    time.sleep(1) # Give server a moment to start
    print("API server started.")
    
    print("Starting PyBullet simulation... (GUI window should appear)")
    
    try:
        # This is the main loop. It must run in the main thread for PyBullet's GUI.
        # It continuously steps the physics and updates the visuals.
        while True:
            world.step()
            # The sleep duration is determined by the physics frequency set in SwarmWorld
            time.sleep(world.physics_dt)
            
    except KeyboardInterrupt:
        print("Simulation interrupted by user.")
    finally:
        # Ensure the simulation is cleanly shut down.
        world.close()
        print("Simulation closed.")


if __name__ == "__main__":
    main()
