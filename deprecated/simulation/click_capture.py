#!/usr/bin/env python3
"""
Simple click capture tool that uses terminal input to mark positions.
Press SPACE while hovering to capture the camera's target position.
"""

import requests
import time
import sys
import select
import termios
import tty

API_BASE = "http://localhost:8000"

class ClickCapture:
    def __init__(self):
        # Get terminal settings
        self.old_settings = termios.tcgetattr(sys.stdin)

    def __enter__(self):
        tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, *args):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def get_key(self, timeout=0.05):
        """Non-blocking key read with timeout"""
        if select.select([sys.stdin], [], [], timeout)[0]:
            return sys.stdin.read(1)
        return None

    def get_state(self):
        """Get current simulation state"""
        try:
            response = requests.get(f"{API_BASE}/state", timeout=1.0)
            if response.ok:
                return response.json()
        except:
            pass
        return None

    def prompt_for_coordinates(self):
        """Prompt user to enter coordinates manually"""
        print("\n" + "="*60)
        print("Enter target coordinates:")
        print("="*60)

        # Restore normal terminal mode temporarily
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

        try:
            x_str = input("X coordinate (meters, -10 to 10): ").strip()
            y_str = input("Y coordinate (meters, -10 to 10): ").strip()
            z_str = input("Z coordinate (meters, 0.1 to 5.0): ").strip()

            x = float(x_str)
            y = float(y_str)
            z = float(z_str)

            # Validate bounds
            if abs(x) > 10 or abs(y) > 10:
                print("❌ X and Y must be within ±10 meters")
                return None
            if z < 0.1 or z > 5.0:
                print("❌ Z must be between 0.1 and 5.0 meters")
                return None

            return (x, y, z)

        except ValueError:
            print("❌ Invalid number format")
            return None
        finally:
            # Re-enter cbreak mode
            tty.setcbreak(sys.stdin.fileno())

    def run(self):
        """Main control loop"""
        print("\n" + "="*60)
        print("  Click Capture Tool")
        print("="*60)
        print("\nControls:")
        print("  SPACE - Enter coordinates manually")
        print("  ESC   - Exit")
        print("\nWaiting for input...\n")

        try:
            while True:
                key = self.get_key()

                if key == ' ':  # Space
                    coords = self.prompt_for_coordinates()
                    if coords:
                        x, y, z = coords
                        print(f"\n✓ Captured coordinates: ({x:.2f}, {y:.2f}, {z:.2f})")
                        print(f"\n📋 For agentic system, use:")
                        print(f"   \"Fly to coordinates {x:.2f}, {y:.2f}, {z:.2f}\"")
                        print("\nPress SPACE for new coordinates, ESC to exit...\n")

                elif key == '\x1b':  # ESC
                    print("\n\nExiting...\n")
                    break

                time.sleep(0.05)

        except KeyboardInterrupt:
            print("\n\nInterrupted. Exiting...\n")

def main():
    """Entry point"""
    try:
        # Check if API is running
        response = requests.get(f"{API_BASE}/state", timeout=2.0)
        if not response.ok:
            print("❌ Error: Simulation API not responding")
            print(f"   Make sure simulation is running on {API_BASE}")
            sys.exit(1)
    except Exception as e:
        print("❌ Error: Cannot connect to simulation API")
        print(f"   Make sure simulation is running on {API_BASE}")
        print(f"   Error: {e}")
        sys.exit(1)

    with ClickCapture() as controller:
        controller.run()

if __name__ == "__main__":
    main()
