#!/usr/bin/env python3
"""
Manual keyboard control for AUS-Lab simulation.
Allows you to fly one drone using keyboard while API controls the rest.
"""

import requests
import time
import sys
import select
import termios
import tty

API_BASE = "http://localhost:8000"

class KeyboardController:
    def __init__(self, drone_id=0):
        self.drone_id = drone_id
        self.position = [0.0, 0.0, 1.0]  # Start at hover height
        self.yaw = 0.0
        self.step = 0.2  # Movement step in meters
        self.yaw_step = 0.3  # Yaw step in radians (~17 degrees)

        # Get terminal settings
        self.old_settings = termios.tcgetattr(sys.stdin)

    def __enter__(self):
        tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, *args):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def get_key(self, timeout=0.1):
        """Non-blocking key read with timeout"""
        if select.select([sys.stdin], [], [], timeout)[0]:
            return sys.stdin.read(1)
        return None

    def send_goto(self):
        """Send current position to API"""
        try:
            response = requests.post(
                f"{API_BASE}/goto",
                json={
                    "id": self.drone_id,
                    "x": self.position[0],
                    "y": self.position[1],
                    "z": self.position[2],
                    "yaw": self.yaw
                },
                timeout=0.5
            )
            return response.ok
        except Exception as e:
            print(f"\nAPI Error: {e}")
            return False

    def get_state(self):
        """Get current drone state from simulation"""
        try:
            response = requests.get(f"{API_BASE}/state", timeout=0.5)
            if response.ok:
                data = response.json()
                drone_data = data['drones'][self.drone_id]
                self.position = drone_data['pos']
                return drone_data
            return None
        except:
            return None

    def run(self):
        """Main control loop"""
        print("=" * 60)
        print("  AUS-Lab Manual Drone Control")
        print("=" * 60)
        print(f"\nControlling Drone {self.drone_id}")
        print("\nControls:")
        print("  W/S - Forward/Backward")
        print("  A/D - Left/Right")
        print("  Q/E - Rotate Left/Right")
        print("  R/F - Up/Down")
        print("  SPACE - Hover at current position")
        print("  H - Return to home (0, 0, 1.5)")
        print("  L - Land")
        print("  1-5 - Switch to controlling drone 1-5")
        print("  ESC or Ctrl+C - Exit")
        print("\nStarting in 2 seconds...")
        time.sleep(2)

        # Initialize position from simulation
        state = self.get_state()
        if state:
            print(f"\nCurrent position: ({self.position[0]:.2f}, {self.position[1]:.2f}, {self.position[2]:.2f})")

        print("\nReady! Use keyboard to fly.\n")

        last_update = time.time()
        update_interval = 0.1  # 10Hz updates

        try:
            while True:
                key = self.get_key(0.05)

                if key:
                    moved = False

                    # Movement controls
                    if key == 'w':
                        self.position[0] += self.step
                        moved = True
                        print(f"Forward  -> ({self.position[0]:.2f}, {self.position[1]:.2f}, {self.position[2]:.2f})")
                    elif key == 's':
                        self.position[0] -= self.step
                        moved = True
                        print(f"Backward -> ({self.position[0]:.2f}, {self.position[1]:.2f}, {self.position[2]:.2f})")
                    elif key == 'a':
                        self.position[1] += self.step
                        moved = True
                        print(f"Left     -> ({self.position[0]:.2f}, {self.position[1]:.2f}, {self.position[2]:.2f})")
                    elif key == 'd':
                        self.position[1] -= self.step
                        moved = True
                        print(f"Right    -> ({self.position[0]:.2f}, {self.position[1]:.2f}, {self.position[2]:.2f})")
                    elif key == 'r':
                        self.position[2] += self.step
                        moved = True
                        print(f"Up       -> ({self.position[0]:.2f}, {self.position[1]:.2f}, {self.position[2]:.2f})")
                    elif key == 'f':
                        self.position[2] -= self.step
                        moved = True
                        print(f"Down     -> ({self.position[0]:.2f}, {self.position[1]:.2f}, {self.position[2]:.2f})")

                    # Rotation
                    elif key == 'q':
                        self.yaw += self.yaw_step
                        moved = True
                        print(f"Rotate Left  -> yaw={self.yaw:.2f} rad ({self.yaw*57.3:.0f}°)")
                    elif key == 'e':
                        self.yaw -= self.yaw_step
                        moved = True
                        print(f"Rotate Right -> yaw={self.yaw:.2f} rad ({self.yaw*57.3:.0f}°)")

                    # Special commands
                    elif key == ' ':
                        # Hover - update position from current actual position
                        state = self.get_state()
                        if state:
                            print(f"Hover at ({self.position[0]:.2f}, {self.position[1]:.2f}, {self.position[2]:.2f})")

                    elif key == 'h':
                        self.position = [0.0, 0.0, 1.5]
                        self.yaw = 0.0
                        moved = True
                        print("Returning to home (0, 0, 1.5)")

                    elif key == 'l':
                        self.position[2] = 0.1
                        moved = True
                        print("Landing...")

                    # Drone selection
                    elif key in '12345':
                        new_id = int(key) - 1
                        if new_id < 5:  # Assuming max 5 drones
                            self.drone_id = new_id
                            state = self.get_state()
                            print(f"\nNow controlling Drone {self.drone_id}")
                            print(f"Position: ({self.position[0]:.2f}, {self.position[1]:.2f}, {self.position[2]:.2f})")

                    # Exit
                    elif key == '\x1b':  # ESC
                        print("\nExiting...")
                        break

                    # Send updated position if moved
                    if moved:
                        # Clamp to safe bounds
                        self.position[0] = max(-10, min(10, self.position[0]))
                        self.position[1] = max(-10, min(10, self.position[1]))
                        self.position[2] = max(0.1, min(5, self.position[2]))

                        self.send_goto()
                        last_update = time.time()

                # Periodic position updates even without input (for smooth control)
                if time.time() - last_update > update_interval:
                    self.send_goto()
                    last_update = time.time()

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        finally:
            print(f"\nDrone {self.drone_id} released to API control")


def main():
    # Check if simulation is running
    try:
        response = requests.get(API_BASE, timeout=2)
        if not response.ok:
            print("Error: Simulation API not responding")
            print(f"Make sure simulation is running: python main.py")
            return 1
    except Exception as e:
        print(f"Error: Cannot connect to simulation at {API_BASE}")
        print("Make sure simulation is running: python main.py")
        return 1

    # Start keyboard controller
    drone_id = 0
    if len(sys.argv) > 1:
        try:
            drone_id = int(sys.argv[1])
        except:
            print(f"Invalid drone ID, using default (0)")

    with KeyboardController(drone_id) as controller:
        controller.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
