"""
Mouse interaction handler for PyBullet GUI.
Captures mouse clicks and converts screen coordinates to 3D world coordinates.
"""

import pybullet as p
import numpy as np
from typing import Optional, Tuple, List


class MouseInteractionHandler:
    """
    Handles mouse input in PyBullet GUI and converts clicks to 3D coordinates.
    Uses ray casting to find intersection with ground plane or objects.
    """

    def __init__(self, physics_client_id: int, ground_height: float = 0.0):
        """
        Initialize mouse handler.

        Args:
            physics_client_id: PyBullet client ID for the simulation
            ground_height: Height of ground plane (default 0.0)
        """
        self.client_id = physics_client_id
        self.ground_height = ground_height

        # Mouse state tracking
        self.last_mouse_state = None
        self.clicked_point = None
        self.click_visual_id = None
        self.text_visual_id = None
        self.last_button_state = 0  # Track previous button state to detect clicks

        # Visual feedback settings
        self.marker_color = [1, 0, 0]  # Red
        self.marker_size = 0.1
        self.marker_duration = 5.0  # seconds

        # Enable mouse picking in PyBullet
        print(f"[MouseHandler DEBUG] Enabling mouse events for client {physics_client_id}")
        p.configureDebugVisualizer(p.COV_ENABLE_MOUSE_PICKING, 1, physicsClientId=self.client_id)
        print(f"[MouseHandler DEBUG] Mouse picking enabled")

    def process_mouse_events(self) -> Optional[Tuple[float, float, float]]:
        """
        Poll mouse events and convert clicks to 3D world coordinates.

        Returns:
            (x, y, z) tuple if new click detected, None otherwise
        """
        # Check MOUSE events directly (like the working test)
        try:
            mouse_events = p.getMouseEvents(physicsClientId=self.client_id)

            # Debug: Print ANY mouse events
            if len(mouse_events) > 0:
                print(f"[MouseHandler] Got {len(mouse_events)} mouse events!")

                # Look for left button press (button 0, state 3)
                for event in mouse_events:
                    event_type = event[0]
                    mouse_x = event[1]
                    mouse_y = event[2]
                    button_index = event[3] if len(event) > 3 else -1
                    button_state = event[4] if len(event) > 4 else -1

                    print(f"[MouseHandler] Event: type={event_type}, pos=({mouse_x},{mouse_y}), btn={button_index}, state={button_state}")

                    # Left click detected
                    if button_index == 0 and button_state == 3:
                        print(f"[MouseHandler] LEFT CLICK at ({mouse_x}, {mouse_y})")
                        world_coords = self._screen_to_world(int(mouse_x), int(mouse_y))
                        if world_coords:
                            self.clicked_point = world_coords
                            self._update_visual_feedback(world_coords)
                            return world_coords

        except Exception as e:
            print(f"[MouseHandler ERROR] {e}")
            import traceback
            traceback.print_exc()

        return None

    def _screen_to_world(self, screen_x: int, screen_y: int) -> Optional[Tuple[float, float, float]]:
        """
        Convert screen coordinates to 3D world coordinates using ray casting.

        Args:
            screen_x: Mouse X position in screen space
            screen_y: Mouse Y position in screen space

        Returns:
            (x, y, z) world coordinates or None if no intersection
        """
        # Get camera parameters
        cam_info = p.getDebugVisualizerCamera(physicsClientId=self.client_id)
        width = cam_info[0]
        height = cam_info[1]
        view_matrix = cam_info[2]
        proj_matrix = cam_info[3]

        # Convert view and projection matrices to numpy arrays
        view_matrix = np.array(view_matrix).reshape(4, 4).T
        proj_matrix = np.array(proj_matrix).reshape(4, 4).T

        # Normalize screen coordinates to [-1, 1]
        norm_x = (2.0 * screen_x / width) - 1.0
        norm_y = 1.0 - (2.0 * screen_y / height)  # Flip Y axis

        # Create ray in clip space
        ray_clip = np.array([norm_x, norm_y, -1.0, 1.0])

        # Transform to eye space
        inv_proj = np.linalg.inv(proj_matrix)
        ray_eye = inv_proj @ ray_clip
        ray_eye = np.array([ray_eye[0], ray_eye[1], -1.0, 0.0])

        # Transform to world space
        inv_view = np.linalg.inv(view_matrix)
        ray_world = (inv_view @ ray_eye)[:3]
        ray_world = ray_world / np.linalg.norm(ray_world)

        # Get camera position (ray origin)
        camera_pos = inv_view[:3, 3]

        # Perform ray casting to find intersection with ground plane
        # Ground plane equation: z = ground_height
        # Ray equation: P = camera_pos + t * ray_world
        # Solve for t when z = ground_height

        if abs(ray_world[2]) < 1e-6:  # Ray parallel to ground
            return None

        t = (self.ground_height - camera_pos[2]) / ray_world[2]

        if t < 0:  # Intersection behind camera
            return None

        # Calculate intersection point
        intersection = camera_pos + t * ray_world

        # Return as tuple (x, y, z)
        return (float(intersection[0]), float(intersection[1]), self.ground_height)

    def _update_visual_feedback(self, coords: Tuple[float, float, float]):
        """
        Draw visual feedback at clicked location.

        Args:
            coords: (x, y, z) world coordinates
        """
        x, y, z = coords

        # Remove old visual markers if they exist
        if self.click_visual_id is not None:
            p.removeUserDebugItem(self.click_visual_id, physicsClientId=self.client_id)
        if self.text_visual_id is not None:
            p.removeUserDebugItem(self.text_visual_id, physicsClientId=self.client_id)

        # Draw cross marker at click location (4 lines forming a cross)
        marker_lines = []
        size = self.marker_size

        # Create cross shape on ground plane
        # Line 1: X-axis
        p.addUserDebugLine(
            [x - size, y, z + 0.01],
            [x + size, y, z + 0.01],
            lineColorRGB=self.marker_color,
            lineWidth=3,
            lifeTime=self.marker_duration,
            physicsClientId=self.client_id
        )

        # Line 2: Y-axis
        p.addUserDebugLine(
            [x, y - size, z + 0.01],
            [x, y + size, z + 0.01],
            lineColorRGB=self.marker_color,
            lineWidth=3,
            lifeTime=self.marker_duration,
            physicsClientId=self.client_id
        )

        # Line 3: Vertical marker
        self.click_visual_id = p.addUserDebugLine(
            [x, y, z],
            [x, y, z + 0.5],
            lineColorRGB=self.marker_color,
            lineWidth=4,
            lifeTime=self.marker_duration,
            physicsClientId=self.client_id
        )

        # Add text label with coordinates
        coord_text = f"Click: ({x:.2f}, {y:.2f}, {z:.2f})"
        self.text_visual_id = p.addUserDebugText(
            coord_text,
            [x, y, z + 0.6],
            textColorRGB=[1, 1, 1],
            textSize=1.2,
            lifeTime=self.marker_duration,
            physicsClientId=self.client_id
        )

    def get_last_clicked_point(self) -> Optional[Tuple[float, float, float]]:
        """
        Get the last clicked point coordinates.

        Returns:
            (x, y, z) tuple or None if no click yet
        """
        return self.clicked_point

    def clear_visual_feedback(self):
        """Remove all visual feedback markers."""
        if self.click_visual_id is not None:
            p.removeUserDebugItem(self.click_visual_id, physicsClientId=self.client_id)
            self.click_visual_id = None

        if self.text_visual_id is not None:
            p.removeUserDebugItem(self.text_visual_id, physicsClientId=self.client_id)
            self.text_visual_id = None