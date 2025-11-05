"""
SwarmWorld: Wrapper around gym-pybullet-drones for multi-UAV swarm simulation.
"""


import time
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from queue import Queue, Empty
from enum import Enum

from gym_pybullet_drones.envs.VelocityAviary import VelocityAviary
from gym_pybullet_drones.utils.enums import DroneModel, Physics

from controllers import PositionController, FormationPlanner, clamp_position, clamp_velocity
from mouse_handler import MouseInteractionHandler


class DroneMode(Enum):
    """Operational modes for individual drones."""
    IDLE = "idle"
    TAKEOFF = "takeoff"
    LANDING = "landing"
    HOVER = "hover"
    GOTO = "goto"
    VELOCITY = "velocity"


class DroneCommand:
    """Command to be executed by a drone."""
    def __init__(self, cmd_type: str, drone_ids: Union[List[int], str], params: Dict):
        self.cmd_type = cmd_type
        self.drone_ids = drone_ids
        self.params = params


class SwarmWorld:
    """
    High-level swarm simulation manager wrapping gym-pybullet-drones.
    Manages drone states, control loops, and command execution.
    """

    def __init__(self,
                 num_drones: int = 5,
                 gui: bool = True,
                 physics_hz: int = 240,
                 control_hz: int = 60):
        """
        Initialize swarm simulation.

        Args:
            num_drones: Number of drones in swarm
            gui: Enable PyBullet GUI
            physics_hz: Physics simulation frequency
            control_hz: Control loop frequency
        """
        self.num_drones = num_drones
        self.gui = gui
        self.physics_hz = physics_hz
        self.control_hz = control_hz
        self.physics_dt = 1.0 / physics_hz
        self.control_dt = 1.0 / control_hz

        # Command queue for thread-safe operation
        self.command_queue: Queue = Queue()

        # Initialize environment
        self._init_environment()

        # Per-drone state
        self.drone_modes: Dict[int, DroneMode] = {i: DroneMode.IDLE for i in range(num_drones)}
        self.target_positions: Dict[int, np.ndarray] = {}
        self.target_yaws: Dict[int, float] = {}
        self.target_velocities: Dict[int, np.ndarray] = {}
        self.target_yaw_rates: Dict[int, float] = {}
        self.hover_positions: Dict[int, np.ndarray] = {}

        # Controllers
        self.position_controllers: Dict[int, PositionController] = {
            i: PositionController() for i in range(num_drones)
        }

        # Battery simulation
        self.batteries: Dict[int, float] = {i: 100.0 for i in range(num_drones)}
        self.battery_drain_rate = 0.5  # percent per minute at hover

        # Health status
        self.health_status: Dict[int, bool] = {i: True for i in range(num_drones)}

        # Timing
        self.sim_time = 0.0
        self.last_control_time = 0.0
        self.step_count = 0

        # Mouse interaction handler (only initialized if GUI enabled)
        self.mouse_handler: Optional[MouseInteractionHandler] = None
        self.last_clicked_coords: Optional[Tuple[float, float, float]] = None

        print(f"[SwarmWorld] Initialized with {num_drones} drones")
        print(f"[SwarmWorld] Physics: {physics_hz}Hz, Control: {control_hz}Hz")

    def _init_environment(self):
        """Initialize gym-pybullet-drones environment."""
        # Calculate initial positions in a grid
        grid_size = int(np.ceil(np.sqrt(self.num_drones)))
        spacing = 0.5

        initial_xyzs = []
        for i in range(self.num_drones):
            row = i // grid_size
            col = i % grid_size
            x = (col - grid_size / 2) * spacing
            y = (row - grid_size / 2) * spacing
            z = 0.1  # Start just above ground
            initial_xyzs.append([x, y, z])

        initial_xyzs = np.array(initial_xyzs)

        # Create VelocityAviary environment (accepts velocity commands)
        self.env = VelocityAviary(
            drone_model=DroneModel.CF2X,
            num_drones=self.num_drones,
            initial_xyzs=initial_xyzs,
            physics=Physics.PYB,
            pyb_freq=self.physics_hz,
            ctrl_freq=self.control_hz,
            gui=self.gui
        )

        # Reset environment
        self.env.reset()

        # Initialize mouse handler if GUI is enabled
        if self.gui:
            physics_client_id = self.env.getPyBulletClient()
            print(f"[SwarmWorld DEBUG] Initializing mouse handler with client_id: {physics_client_id}")
            self.mouse_handler = MouseInteractionHandler(
                physics_client_id=physics_client_id,
                ground_height=0.0
            )
            print("[SwarmWorld] Mouse interaction enabled - Click in GUI to capture coordinates!")
        else:
            print("[SwarmWorld DEBUG] GUI disabled, mouse handler NOT initialized")

    def enqueue_command(self, command: DroneCommand):
        """Thread-safe command queuing."""
        self.command_queue.put(command)

    def step(self) -> bool:
        """
        Execute one simulation step.

        Returns:
            True if simulation should continue, False to stop
        """
        # Handle mouse input if GUI enabled
        if self.mouse_handler is not None:
            clicked_coords = self.mouse_handler.process_mouse_events()
            if clicked_coords is not None:
                self.last_clicked_coords = clicked_coords
                print(f"\n[Mouse Click] Coordinates: ({clicked_coords[0]:.2f}, {clicked_coords[1]:.2f}, {clicked_coords[2]:.2f})")
                print(f"[Mouse Click] Copy this for agentic system: {clicked_coords[0]:.2f}, {clicked_coords[1]:.2f}, {clicked_coords[2]:.2f}")

        # Process queued commands
        self._process_commands()

        # Control update if it's time
        if self.sim_time - self.last_control_time >= self.control_dt - 1e-6:
            self._control_update()
            self.last_control_time = self.sim_time

        # Step physics simulation
        # Gymnasium API returns 5 values: obs, rewards, terminated, truncated, infos
        # Older gym-pybullet-drones might use old Gym API (4 values)
        step_result = self.env.step(self._compute_actions())
        if len(step_result) == 5:
            obs, rewards, terminated, truncated, infos = step_result
            dones = {i: terminated.get(i, False) or truncated.get(i, False)
                    for i in range(self.num_drones)} if isinstance(terminated, dict) else \
                   {i: terminated or truncated for i in range(self.num_drones)}
        else:
            obs, rewards, dones, infos = step_result

        # Update simulation time
        self.sim_time += self.physics_dt
        self.step_count += 1

        # Update battery levels
        if self.step_count % self.physics_hz == 0:  # Once per second
            self._update_batteries()

        # Check health status
        self._check_health()

        return not all(dones.values())

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
            for drone_id in drone_ids:
                self._takeoff_drone(drone_id, altitude)

        elif cmd.cmd_type == "land":
            for drone_id in drone_ids:
                self._land_drone(drone_id)

        elif cmd.cmd_type == "hover":
            for drone_id in drone_ids:
                self._hover_drone(drone_id)

        elif cmd.cmd_type == "goto":
            drone_id = cmd.params["id"]
            target = np.array([cmd.params["x"], cmd.params["y"], cmd.params["z"]])
            yaw = cmd.params.get("yaw", 0.0)
            self._goto_position(drone_id, target, yaw)

        elif cmd.cmd_type == "velocity":
            drone_id = cmd.params["id"]
            vel = np.array([cmd.params["vx"], cmd.params["vy"], cmd.params["vz"]])
            yaw_rate = cmd.params.get("yaw_rate", 0.0)
            self._set_velocity(drone_id, vel, yaw_rate)

        elif cmd.cmd_type == "formation":
            self._set_formation(cmd.params)

        elif cmd.cmd_type == "reset":
            self._reset_simulation()

        elif cmd.cmd_type == "spawn":
            self._respawn(cmd.params.get("num", 5))

    def _takeoff_drone(self, drone_id: int, altitude: float):
        """Command drone to take off to target altitude."""
        current_pos = self._get_position(drone_id)
        target_pos = current_pos.copy()
        target_pos[2] = altitude

        self.target_positions[drone_id] = clamp_position(target_pos)
        self.target_yaws[drone_id] = 0.0
        self.drone_modes[drone_id] = DroneMode.TAKEOFF
        print(f"[SwarmWorld] Drone {drone_id} taking off to altitude {altitude}m")

    def _land_drone(self, drone_id: int):
        """Command drone to land."""
        current_pos = self._get_position(drone_id)
        target_pos = current_pos.copy()
        target_pos[2] = 0.05  # Just above ground

        self.target_positions[drone_id] = target_pos
        self.target_yaws[drone_id] = 0.0
        self.drone_modes[drone_id] = DroneMode.LANDING
        print(f"[SwarmWorld] Drone {drone_id} landing")

    def _hover_drone(self, drone_id: int):
        """Command drone to hover at current position."""
        current_pos = self._get_position(drone_id)
        current_yaw = self._get_yaw(drone_id)

        self.hover_positions[drone_id] = current_pos.copy()
        self.target_positions[drone_id] = current_pos.copy()
        self.target_yaws[drone_id] = current_yaw
        self.drone_modes[drone_id] = DroneMode.HOVER
        print(f"[SwarmWorld] Drone {drone_id} hovering at {current_pos}")

    def _goto_position(self, drone_id: int, target: np.ndarray, yaw: float):
        """Command drone to go to target position."""
        clamped_target = clamp_position(target)
        self.target_positions[drone_id] = clamped_target
        self.target_yaws[drone_id] = yaw
        self.drone_modes[drone_id] = DroneMode.GOTO
        print(f"[SwarmWorld] Drone {drone_id} going to {clamped_target}")

    def _set_velocity(self, drone_id: int, velocity: np.ndarray, yaw_rate: float):
        """Command drone velocity directly."""
        clamped_vel = clamp_velocity(velocity, max_vel=2.0)
        self.target_velocities[drone_id] = clamped_vel
        self.target_yaw_rates[drone_id] = np.clip(yaw_rate, -np.pi, np.pi)
        self.drone_modes[drone_id] = DroneMode.VELOCITY
        print(f"[SwarmWorld] Drone {drone_id} velocity set to {clamped_vel}")

    def _set_formation(self, params: Dict):
        """Set swarm formation."""
        pattern = params["pattern"]
        center = np.array(params["center"])
        spacing = params.get("spacing", 1.0)
        radius = params.get("radius", 1.5)
        axis = params.get("axis", "x")

        # Generate formation positions
        if pattern == "line":
            positions = FormationPlanner.line(center, self.num_drones, spacing, axis)
        elif pattern == "circle":
            positions = FormationPlanner.circle(center, self.num_drones, radius)
        elif pattern == "grid":
            positions = FormationPlanner.grid(center, self.num_drones, spacing)
        elif pattern == "v":
            positions = FormationPlanner.v_formation(center, self.num_drones, spacing)
        else:
            print(f"[SwarmWorld] Unknown formation pattern: {pattern}")
            return

        # Assign target positions to each drone
        for i, pos in enumerate(positions):
            if i < self.num_drones:
                self.target_positions[i] = clamp_position(pos)
                self.target_yaws[i] = 0.0
                self.drone_modes[i] = DroneMode.GOTO

        print(f"[SwarmWorld] Formation '{pattern}' commanded for {self.num_drones} drones")

    def _control_update(self):
        """Update control commands for all drones."""
        for drone_id in range(self.num_drones):
            mode = self.drone_modes[drone_id]

            if mode in [DroneMode.TAKEOFF, DroneMode.LANDING, DroneMode.GOTO, DroneMode.HOVER]:
                # Position control mode
                if drone_id in self.target_positions:
                    current_pos = self._get_position(drone_id)
                    current_yaw = self._get_yaw(drone_id)
                    target_pos = self.target_positions[drone_id]
                    target_yaw = self.target_yaws.get(drone_id, 0.0)

                    # Check if reached target (for takeoff/landing completion)
                    dist = np.linalg.norm(target_pos - current_pos)
                    if mode == DroneMode.LANDING and current_pos[2] < 0.15:
                        self.drone_modes[drone_id] = DroneMode.IDLE
                        self.target_velocities[drone_id] = np.zeros(3)
                    elif mode == DroneMode.TAKEOFF and dist < 0.1:
                        self.drone_modes[drone_id] = DroneMode.HOVER
                        self.hover_positions[drone_id] = current_pos.copy()

            elif mode == DroneMode.VELOCITY:
                # Direct velocity control - already set in target_velocities
                pass

            elif mode == DroneMode.IDLE:
                # Keep motors at minimum
                self.target_velocities[drone_id] = np.zeros(3)

    def _compute_actions(self) -> np.ndarray:
        """
        Compute motor actions for all drones based on current control mode.

        Returns:
            Action array for gym-pybullet-drones environment
        """
        actions = np.zeros((self.num_drones, 4))

        for drone_id in range(self.num_drones):
            mode = self.drone_modes[drone_id]

            if mode in [DroneMode.TAKEOFF, DroneMode.LANDING, DroneMode.GOTO, DroneMode.HOVER]:
                # Use position controller
                if drone_id in self.target_positions:
                    current_pos = self._get_position(drone_id)
                    current_yaw = self._get_yaw(drone_id)
                    target_pos = self.target_positions[drone_id]
                    target_yaw = self.target_yaws.get(drone_id, 0.0)

                    vel_cmd, yaw_rate_cmd = self.position_controllers[drone_id].compute_control(
                        current_pos, target_pos, current_yaw, target_yaw, self.control_dt
                    )

                    # Store computed velocity
                    self.target_velocities[drone_id] = vel_cmd
                    self.target_yaw_rates[drone_id] = yaw_rate_cmd

                    # Convert to VelocityAviary format: [vx_dir, vy_dir, vz_dir, speed_fraction]
                    # VelocityAviary expects direction vector + speed magnitude
                    speed = np.linalg.norm(vel_cmd)
                    if speed > 0.01:
                        # Direction (will be normalized by VelocityAviary)
                        direction = vel_cmd / speed
                        # Speed as fraction of max (SPEED_LIMIT in VelocityAviary ~0.25 m/s)
                        # Our max velocity is 2.0 m/s, normalize to [0, 1]
                        speed_frac = min(speed / 2.0, 1.0)
                        actions[drone_id] = [direction[0], direction[1], direction[2], speed_frac]
                    else:
                        # Hovering or very small movement
                        actions[drone_id] = [0, 0, 0, 0]
                else:
                    actions[drone_id] = [0, 0, 0, 0]

            elif mode == DroneMode.VELOCITY:
                # Direct velocity command - convert to VelocityAviary format
                vel = self.target_velocities.get(drone_id, np.zeros(3))
                speed = np.linalg.norm(vel)
                if speed > 0.01:
                    direction = vel / speed
                    speed_frac = min(speed / 2.0, 1.0)
                    actions[drone_id] = [direction[0], direction[1], direction[2], speed_frac]
                else:
                    actions[drone_id] = [0, 0, 0, 0]

            else:  # IDLE
                actions[drone_id] = [0, 0, 0, 0]

        return actions

    def _get_position(self, drone_id: int) -> np.ndarray:
        """Get current position of drone."""
        state = self.env._getDroneStateVector(drone_id)
        return state[0:3]

    def _get_velocity(self, drone_id: int) -> np.ndarray:
        """Get current velocity of drone."""
        state = self.env._getDroneStateVector(drone_id)
        return state[10:13]

    def _get_yaw(self, drone_id: int) -> float:
        """Get current yaw of drone."""
        state = self.env._getDroneStateVector(drone_id)
        # Extract yaw from quaternion (simplified)
        quat = state[3:7]
        # For simplicity, use approximation
        yaw = np.arctan2(2.0 * (quat[3] * quat[2] + quat[0] * quat[1]),
                        1.0 - 2.0 * (quat[1]**2 + quat[2]**2))
        return yaw

    def _update_batteries(self):
        """Update battery levels based on usage."""
        drain_per_second = self.battery_drain_rate / 60.0
        for drone_id in range(self.num_drones):
            if self.drone_modes[drone_id] != DroneMode.IDLE:
                self.batteries[drone_id] = max(0.0, self.batteries[drone_id] - drain_per_second)

    def _check_health(self):
        """Check and update health status of drones."""
        for drone_id in range(self.num_drones):
            pos = self._get_position(drone_id)
            # Check if out of bounds or battery dead
            if (abs(pos[0]) > 15.0 or abs(pos[1]) > 15.0 or
                pos[2] < 0 or pos[2] > 10.0 or
                self.batteries[drone_id] <= 0.0):
                self.health_status[drone_id] = False
            else:
                self.health_status[drone_id] = True

    def get_state(self) -> Dict:
        """
        Get current state of all drones.

        Returns:
            Dictionary with state information
        """
        states = []
        for drone_id in range(self.num_drones):
            pos = self._get_position(drone_id)
            vel = self._get_velocity(drone_id)
            yaw = self._get_yaw(drone_id)

            states.append({
                "id": drone_id,
                "pos": pos.tolist(),
                "vel": vel.tolist(),
                "yaw": float(yaw),
                "battery": float(self.batteries[drone_id]),
                "healthy": bool(self.health_status[drone_id])
            })

        return {
            "drones": states,
            "timestamp": float(self.sim_time)
        }

    def _reset_simulation(self):
        """Reset simulation to initial state."""
        print("[SwarmWorld] Resetting simulation")
        self.env.reset()
        self.sim_time = 0.0
        self.last_control_time = 0.0
        self.step_count = 0

        # Reset all drone states
        for i in range(self.num_drones):
            self.drone_modes[i] = DroneMode.IDLE
            self.batteries[i] = 100.0
            self.health_status[i] = True
            self.position_controllers[i].reset()

        self.target_positions.clear()
        self.target_yaws.clear()
        self.target_velocities.clear()
        self.target_yaw_rates.clear()
        self.hover_positions.clear()

    def _respawn(self, num_drones: int):
        """Respawn simulation with different number of drones."""
        print(f"[SwarmWorld] Respawning with {num_drones} drones")
        self.env.close()
        self.num_drones = num_drones
        self._init_environment()

        # Reinitialize all state
        self.drone_modes = {i: DroneMode.IDLE for i in range(num_drones)}
        self.batteries = {i: 100.0 for i in range(num_drones)}
        self.health_status = {i: True for i in range(num_drones)}
        self.position_controllers = {i: PositionController() for i in range(num_drones)}

        self.target_positions.clear()
        self.target_yaws.clear()
        self.target_velocities.clear()
        self.target_yaw_rates.clear()
        self.hover_positions.clear()

        self.sim_time = 0.0
        self.last_control_time = 0.0
        self.step_count = 0

    def close(self):
        """Clean up and close simulation."""
        print("[SwarmWorld] Closing simulation")
        self.env.close()
