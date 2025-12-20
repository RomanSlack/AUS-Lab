import numpy as np
from typing import List

class HivemindController:
    """
    Controls the entire swarm as a single entity.
    """

    def __init__(self, num_drones: int, initial_positions: np.ndarray):
        """
        Initialize the Hivemind controller.

        Args:
            num_drones: The number of drones in the swarm.
            initial_positions: The initial positions of the drones.
        """
        self.num_drones = num_drones
        self.initial_positions = initial_positions
        self.relative_positions = self.initial_positions - np.mean(self.initial_positions, axis=0)

        self.target_position = np.mean(self.initial_positions, axis=0)
        self.target_yaw = 0.0
        self.target_scale = 1.0

    def set_target(self, position: np.ndarray, yaw: float, scale: float):
        """
        Set the target state of the swarm.

        Args:
            position: The target center position of the swarm.
            yaw: The target yaw of the swarm.
            scale: The target scale of the swarm.
        """
        self.target_position = position
        self.target_yaw = yaw
        self.target_scale = scale

    def update(self) -> np.ndarray:
        """
        Update the target positions of the individual drones.

        Returns:
            An array of target positions for each drone.
        """
        # Create rotation matrix from yaw
        rotation_matrix = np.array([
            [np.cos(self.target_yaw), -np.sin(self.target_yaw), 0],
            [np.sin(self.target_yaw), np.cos(self.target_yaw), 0],
            [0, 0, 1]
        ])

        # Apply rotation and scale to relative positions
        scaled_rotated_positions = self.relative_positions * self.target_scale
        transformed_positions = np.dot(scaled_rotated_positions, rotation_matrix.T)

        # Add target position to get absolute target positions
        drone_target_positions = self.target_position + transformed_positions

        return drone_target_positions
