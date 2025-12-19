"""
SwarmWorld using Rust physics engine for high-performance drone simulation.
Drop-in replacement for the PyBullet-based SwarmWorld.
"""

import time
from typing import Dict, List, Optional, Union
from queue import Queue, Empty
from enum import Enum

import drone_physics


class DroneCommand:
    """Command to be executed by a drone."""
    def __init__(self, cmd_type: str, drone_ids: Union[List[int], str], params: Dict):
        self.cmd_type = cmd_type
        self.drone_ids = drone_ids
        self.params = params


class SwarmWorldRust:
    """
    High-performance swarm simulation using Rust physics engine.
    Provides the same interface as the PyBullet-based SwarmWorld.
    """

    def __init__(self,
                 num_drones: int = 5,
                 gui: bool = True,
                 physics_hz: int = 240,
                 control_hz: int = 60,
                 use_custom_renderer: bool = True):
        """
        Initialize swarm simulation with Rust physics.

        Args:
            num_drones: Number of drones in swarm
            gui: Ignored (Rust physics is headless, Three.js handles viz)
            physics_hz: Physics simulation frequency
            control_hz: Control loop frequency (used for battery updates)
            use_custom_renderer: Ignored (Three.js handles rendering)
        """
        self.num_drones = num_drones
        self.physics_hz = physics_hz
        self.control_hz = control_hz
        self.physics_dt = 1.0 / physics_hz
        self.control_dt = 1.0 / control_hz

        # Command queue for thread-safe operation
        self.command_queue: Queue = Queue()

        # Initialize Rust physics engine
        self.swarm = drone_physics.RustSwarm(num_drones, physics_hz)

        # Speed multiplier (for running multiple steps)
        self.speed_multiplier: float = 1.0

        # Battery drain rate
        self.battery_drain_rate = 0.5  # percent per minute

        # Step tracking
        self.step_count = 0
        self.last_battery_update = 0.0

        print(f"[SwarmWorldRust] Initialized with {num_drones} drones (Rust physics)")
        print(f"[SwarmWorldRust] Physics: {physics_hz}Hz, Control: {control_hz}Hz")

    def enqueue_command(self, command: DroneCommand):
        """Thread-safe command queuing."""
        self.command_queue.put(command)

    def step(self) -> bool:
        """
        Execute one simulation step.

        Returns:
            True (simulation continues indefinitely)
        """
        # Process queued commands
        self._process_commands()

        # Calculate how many physics steps to run based on speed multiplier
        steps_to_run = max(1, int(self.speed_multiplier))

        # Step physics (Rust handles all the heavy lifting)
        self.swarm.step_multiple(steps_to_run)
        self.step_count += steps_to_run

        # Update battery levels periodically
        sim_time = self.swarm.get_time()
        if sim_time - self.last_battery_update >= 1.0:
            self.swarm.update_batteries(self.battery_drain_rate)
            self.last_battery_update = sim_time

        return True

    def _process_commands(self):
        """Process all queued commands."""
        while True:
            try:
                cmd = self.command_queue.get_nowait()
                self._execute_command(cmd)
            except Empty:
                break

    def _execute_command(self, cmd: DroneCommand):
        """Execute a single command."""
        # Resolve drone IDs
        if cmd.drone_ids == "all":
            drone_ids = list(range(self.num_drones))
        else:
            drone_ids = cmd.drone_ids

        # Execute command by type
        if cmd.cmd_type == "takeoff":
            altitude = cmd.params.get("altitude", 1.0)
            self.swarm.takeoff(drone_ids, altitude)
            print(f"[SwarmWorldRust] Takeoff to {altitude}m")

        elif cmd.cmd_type == "land":
            self.swarm.land(drone_ids)
            print(f"[SwarmWorldRust] Landing")

        elif cmd.cmd_type == "hover":
            self.swarm.hover(drone_ids)
            print(f"[SwarmWorldRust] Hovering")

        elif cmd.cmd_type == "goto":
            drone_id = cmd.params["id"]
            x, y, z = cmd.params["x"], cmd.params["y"], cmd.params["z"]
            yaw = cmd.params.get("yaw", 0.0)
            self.swarm.goto(drone_id, x, y, z, yaw)
            print(f"[SwarmWorldRust] Drone {drone_id} going to ({x:.2f}, {y:.2f}, {z:.2f})")

        elif cmd.cmd_type == "velocity":
            drone_id = cmd.params["id"]
            vx, vy, vz = cmd.params["vx"], cmd.params["vy"], cmd.params["vz"]
            yaw_rate = cmd.params.get("yaw_rate", 0.0)
            self.swarm.velocity(drone_id, vx, vy, vz, yaw_rate)
            print(f"[SwarmWorldRust] Drone {drone_id} velocity set")

        elif cmd.cmd_type == "formation":
            pattern = cmd.params["pattern"]
            center = cmd.params["center"]
            spacing = cmd.params.get("spacing", 1.0)
            radius = cmd.params.get("radius", 1.5)
            axis = cmd.params.get("axis", "x")

            if pattern == "line":
                self.swarm.formation_line(center, spacing, axis)
            elif pattern == "circle":
                self.swarm.formation_circle(center, radius)
            elif pattern == "grid":
                self.swarm.formation_grid(center, spacing)
            elif pattern == "v":
                self.swarm.formation_v(center, spacing)
            else:
                print(f"[SwarmWorldRust] Unknown formation: {pattern}")
                return

            print(f"[SwarmWorldRust] Formation '{pattern}' commanded")

        elif cmd.cmd_type == "reset":
            self.swarm.reset()
            self.step_count = 0
            self.last_battery_update = 0.0
            print(f"[SwarmWorldRust] Reset")

        elif cmd.cmd_type == "spawn":
            num = cmd.params.get("num", 5)
            self.swarm.respawn(num)
            self.num_drones = num
            self.step_count = 0
            self.last_battery_update = 0.0
            print(f"[SwarmWorldRust] Respawned with {num} drones")

        elif cmd.cmd_type == "speed":
            speed = cmd.params.get("speed", 1.0)
            self.speed_multiplier = speed
            self.swarm.set_speed(speed)
            print(f"[SwarmWorldRust] Speed set to {speed:.1f}x")

        elif cmd.cmd_type == "waypoint":
            x = cmd.params.get("x", 0.0)
            y = cmd.params.get("y", 0.0)
            z = cmd.params.get("z", 1.5)
            self.swarm.waypoint(x, y, z)
            print(f"[SwarmWorldRust] Waypoint ({x:.2f}, {y:.2f}, {z:.2f})")

        elif cmd.cmd_type == "monitor":
            x = cmd.params.get("x", 0.0)
            y = cmd.params.get("y", 0.0)
            z = cmd.params.get("z", 1.5)
            self.swarm.monitor(x, y, z)
            print(f"[SwarmWorldRust] Monitor mode at ({x:.2f}, {y:.2f}, {z:.2f})")

    def get_state(self) -> Dict:
        """
        Get current state of all drones.

        Returns:
            Dictionary with state information
        """
        states = self.swarm.get_states()

        drone_states = []
        for state in states:
            drone_states.append({
                "id": state.id,
                "pos": list(state.pos),
                "vel": list(state.vel),
                "yaw": float(state.yaw),
                "battery": float(state.battery),
                "healthy": bool(state.healthy)
            })

        return {
            "drones": drone_states,
            "timestamp": float(self.swarm.get_time())
        }

    def close(self):
        """Clean up (nothing to do for Rust physics)."""
        print("[SwarmWorldRust] Closed")
