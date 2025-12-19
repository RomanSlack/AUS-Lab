"""
Simple PID controllers and formation planners for UAV swarm control.
"""

import numpy as np
from typing import List, Tuple, Dict


class PIDController:
    """Simple PID controller with integral anti-windup and output clamping."""

    def __init__(self, kp: float, ki: float, kd: float, output_limits: Tuple[float, float] = (-np.inf, np.inf)):
        """
        Initialize PID controller.

        Args:
            kp: Proportional gain
            ki: Integral gain
            kd: Derivative gain
            output_limits: (min, max) tuple for output clamping
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limits = output_limits

        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = None

    def reset(self):
        """Reset controller state."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = None

    def update(self, error: float, dt: float) -> float:
        """
        Update PID controller with new error measurement.

        Args:
            error: Current error (setpoint - measurement)
            dt: Time step in seconds

        Returns:
            Control output
        """
        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self.integral += error * dt
        i_term = self.ki * self.integral

        # Derivative term
        if dt > 0:
            derivative = (error - self.prev_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative

        # Calculate output
        output = p_term + i_term + d_term

        # Clamp output
        output = np.clip(output, self.output_limits[0], self.output_limits[1])

        # Anti-windup: back-calculate integral if we're saturated
        if output != p_term + i_term + d_term:
            # We hit limits, reduce integral
            self.integral -= error * dt * 0.5

        self.prev_error = error

        return output


class PositionController:
    """3D position controller using separate PID controllers for x, y, z, and yaw."""

    def __init__(self,
                 pos_gains: Tuple[float, float, float] = (2.0, 0.01, 0.5),
                 yaw_gains: Tuple[float, float, float] = (2.0, 0.0, 0.3),
                 max_velocity: float = 2.0,
                 max_yaw_rate: float = np.pi):
        """
        Initialize position controller.

        Args:
            pos_gains: (kp, ki, kd) for position control
            yaw_gains: (kp, ki, kd) for yaw control
            max_velocity: Maximum velocity in m/s
            max_yaw_rate: Maximum yaw rate in rad/s
        """
        self.pid_x = PIDController(*pos_gains, output_limits=(-max_velocity, max_velocity))
        self.pid_y = PIDController(*pos_gains, output_limits=(-max_velocity, max_velocity))
        self.pid_z = PIDController(*pos_gains, output_limits=(-max_velocity, max_velocity))
        self.pid_yaw = PIDController(*yaw_gains, output_limits=(-max_yaw_rate, max_yaw_rate))

    def reset(self):
        """Reset all PID controllers."""
        self.pid_x.reset()
        self.pid_y.reset()
        self.pid_z.reset()
        self.pid_yaw.reset()

    def set_max_velocity(self, max_velocity: float):
        """Update maximum velocity for all position PIDs."""
        self.pid_x.output_limits = (-max_velocity, max_velocity)
        self.pid_y.output_limits = (-max_velocity, max_velocity)
        self.pid_z.output_limits = (-max_velocity, max_velocity)

    def compute_control(self,
                       current_pos: np.ndarray,
                       target_pos: np.ndarray,
                       current_yaw: float,
                       target_yaw: float,
                       dt: float) -> Tuple[np.ndarray, float]:
        """
        Compute velocity commands to reach target position and yaw.

        Args:
            current_pos: Current [x, y, z] position
            target_pos: Target [x, y, z] position
            current_yaw: Current yaw angle in radians
            target_yaw: Target yaw angle in radians
            dt: Time step in seconds

        Returns:
            (velocity_xyz, yaw_rate) tuple
        """
        # Position errors
        error_x = target_pos[0] - current_pos[0]
        error_y = target_pos[1] - current_pos[1]
        error_z = target_pos[2] - current_pos[2]

        # Yaw error (normalize to [-pi, pi])
        error_yaw = target_yaw - current_yaw
        error_yaw = np.arctan2(np.sin(error_yaw), np.cos(error_yaw))

        # Compute control outputs
        vx = self.pid_x.update(error_x, dt)
        vy = self.pid_y.update(error_y, dt)
        vz = self.pid_z.update(error_z, dt)
        yaw_rate = self.pid_yaw.update(error_yaw, dt)

        return np.array([vx, vy, vz]), yaw_rate


class FormationPlanner:
    """Plans target positions for different swarm formations."""

    @staticmethod
    def line(center: np.ndarray, num_drones: int, spacing: float = 1.0, axis: str = 'x') -> List[np.ndarray]:
        """
        Generate line formation.

        Args:
            center: Center point [x, y, z]
            num_drones: Number of drones
            spacing: Distance between drones
            axis: 'x' or 'y' axis for line direction

        Returns:
            List of target positions
        """
        positions = []
        start_offset = -(num_drones - 1) * spacing / 2.0

        for i in range(num_drones):
            pos = center.copy()
            offset = start_offset + i * spacing

            if axis == 'x':
                pos[0] += offset
            elif axis == 'y':
                pos[1] += offset
            else:
                raise ValueError(f"Invalid axis: {axis}. Use 'x' or 'y'.")

            positions.append(pos)

        return positions

    @staticmethod
    def circle(center: np.ndarray, num_drones: int, radius: float = 1.5) -> List[np.ndarray]:
        """
        Generate circular formation.

        Args:
            center: Center point [x, y, z]
            num_drones: Number of drones
            radius: Circle radius

        Returns:
            List of target positions
        """
        positions = []

        for i in range(num_drones):
            angle = 2 * np.pi * i / num_drones
            pos = center.copy()
            pos[0] += radius * np.cos(angle)
            pos[1] += radius * np.sin(angle)
            positions.append(pos)

        return positions

    @staticmethod
    def grid(center: np.ndarray, num_drones: int, spacing: float = 1.0) -> List[np.ndarray]:
        """
        Generate grid formation (as square as possible).

        Args:
            center: Center point [x, y, z]
            num_drones: Number of drones
            spacing: Distance between drones in grid

        Returns:
            List of target positions
        """
        positions = []

        # Calculate grid dimensions (try to make it square)
        cols = int(np.ceil(np.sqrt(num_drones)))
        rows = int(np.ceil(num_drones / cols))

        # Center the grid
        start_x = -(cols - 1) * spacing / 2.0
        start_y = -(rows - 1) * spacing / 2.0

        for i in range(num_drones):
            row = i // cols
            col = i % cols

            pos = center.copy()
            pos[0] += start_x + col * spacing
            pos[1] += start_y + row * spacing
            positions.append(pos)

        return positions

    @staticmethod
    def v_formation(center: np.ndarray, num_drones: int, spacing: float = 1.0, angle: float = np.pi/6) -> List[np.ndarray]:
        """
        Generate V formation (like flying geese).

        Args:
            center: Center point [x, y, z]
            num_drones: Number of drones
            spacing: Distance between drones
            angle: V-angle from center line (radians)

        Returns:
            List of target positions
        """
        positions = []

        # Leader at front
        positions.append(center.copy())

        # Followers in V behind leader
        for i in range(1, num_drones):
            pos = center.copy()
            side = 1 if i % 2 == 0 else -1
            offset_back = (i + 1) // 2

            pos[0] -= offset_back * spacing * np.cos(angle)
            pos[1] += side * offset_back * spacing * np.sin(angle)
            positions.append(pos)

        return positions


def clamp_position(pos: np.ndarray,
                  bounds_xy: Tuple[float, float] = (-10.0, 10.0),
                  bounds_z: Tuple[float, float] = (0.1, 5.0)) -> np.ndarray:
    """
    Clamp position to safe boundaries.

    Args:
        pos: Position [x, y, z]
        bounds_xy: (min, max) for x and y
        bounds_z: (min, max) for z

    Returns:
        Clamped position
    """
    clamped = pos.copy()
    clamped[0] = np.clip(clamped[0], bounds_xy[0], bounds_xy[1])
    clamped[1] = np.clip(clamped[1], bounds_xy[0], bounds_xy[1])
    clamped[2] = np.clip(clamped[2], bounds_z[0], bounds_z[1])
    return clamped


def clamp_velocity(vel: np.ndarray, max_vel: float = 2.0) -> np.ndarray:
    """
    Clamp velocity magnitude.

    Args:
        vel: Velocity [vx, vy, vz]
        max_vel: Maximum velocity magnitude

    Returns:
        Clamped velocity
    """
    magnitude = np.linalg.norm(vel)
    if magnitude > max_vel:
        return vel * (max_vel / magnitude)
    return vel
