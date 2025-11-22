
import subprocess
import os
import time
from hive_mind import HiveMindController

def run_simulation_process():
    """
    Runs the simulation in a separate process.
    """
    simulation_path = os.path.join(os.path.dirname(__file__), "..", "simulation", "main.py")
    log_file = open("simulation.log", "w")
    process = subprocess.Popen(["python", simulation_path], stdout=log_file, stderr=subprocess.STDOUT)
    print("Starting simulation...")
    return process

def main():
    """
    Main function to run the agentic layer and control the simulation interactively.
    """
    plan = {"area": "0,0,5", "swarm": {"formation": "line", "behavior": "patrol"}}
    num_drones = 4
    hive_mind = HiveMindController(plan, num_drones=num_drones)

    simulation_process = run_simulation_process()
    
    try:
        hive_mind.start()
        
        # Initial status display
        time.sleep(1) # Give drones a moment to get into initial formation
        hive_mind.get_and_print_state()

        while True:
            command_str = input("> ").lower().strip()
            parts = command_str.split()
            if not parts:
                continue

            command = parts[0]

            if command == "exit":
                break
            elif command == "status":
                hive_mind.get_and_print_state()
            elif command == "formation" and len(parts) == 2:
                hive_mind.set_formation(parts[1])
                time.sleep(0.5) # allow command to propagate
                hive_mind.get_and_print_state()
            elif command == "move" and len(parts) == 4:
                try:
                    coords = [float(p) for p in parts[1:]]
                    hive_mind.move_center_to(coords)
                    time.sleep(0.5)
                    hive_mind.get_and_print_state()
                except ValueError:
                    print("Invalid coordinates. Please use numbers (e.g., move 10 15 5).")
            else:
                print(f"Unknown command: '{command_str}'")
                print("Available: formation <line|circle>, move <x y z>, status, exit")


    except (KeyboardInterrupt, RuntimeError) as e:
        print(f"\nController stopped: {e}")
    finally:
        print("Terminating simulation...")
        simulation_process.terminate()
        simulation_process.wait()
        print("Simulation terminated.")

if __name__ == "__main__":
    main()
