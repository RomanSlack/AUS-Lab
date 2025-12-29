"""
Custom OpenCV-based renderer for PyBullet simulation.
Provides stable, flicker-free visualization using GPU-accelerated camera rendering.
"""

import cv2
import numpy as np
import pybullet as p
from typing import Optional, Tuple
import threading
import time


class CustomRenderer:
    """
    High-performance OpenCV-based renderer for PyBullet simulations.

    Uses PyBullet's getCameraImage API for GPU-accelerated rendering,
    then displays in a stable OpenCV window. This bypasses PyBullet's
    buggy GUI system while maintaining full GPU acceleration.
    """

    def __init__(self,
                 physics_client_id: int,
                 window_width: int = 1920,
                 window_height: int = 1080,
                 camera_distance: float = 8.0,
                 camera_yaw: float = 50,
                 camera_pitch: float = -35,
                 camera_target: Tuple[float, float, float] = (0, 0, 0),
                 render_fps: int = 60):
        """
        Initialize custom renderer.

        Args:
            physics_client_id: PyBullet physics client ID
            window_width: Render width in pixels
            window_height: Render height in pixels
            camera_distance: Distance from target
            camera_yaw: Camera yaw angle (degrees)
            camera_pitch: Camera pitch angle (degrees)
            camera_target: Camera look-at point (x, y, z)
            render_fps: Target rendering FPS
        """
        self.client_id = physics_client_id
        self.width = window_width
        self.height = window_height
        self.render_fps = render_fps
        self.frame_time = 1.0 / render_fps

        # Camera parameters
        self.camera_distance = camera_distance
        self.camera_yaw = camera_yaw
        self.camera_pitch = camera_pitch
        self.camera_target = list(camera_target)

        # OpenCV window
        self.window_name = "AUS-Lab Drone Swarm Simulation"
        print(f"[CustomRenderer] Creating OpenCV window...")
        try:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self.window_name, window_width, window_height)
            print(f"[CustomRenderer] OpenCV window created successfully")
        except Exception as e:
            print(f"[CustomRenderer] ERROR creating OpenCV window: {e}")
            raise

        # Mouse interaction state
        self.mouse_pressed = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.last_clicked_coords: Optional[Tuple[float, float, float]] = None

        # Set up mouse callback
        cv2.setMouseCallback(self.window_name, self._mouse_callback)

        # Compute view and projection matrices
        self._update_camera_matrices()

        # Performance tracking
        self.last_render_time = time.time()
        self.frame_count = 0
        self.fps_counter = 0
        self.fps_last_time = time.time()
        self.render_skip_counter = 99  # Start high so first call renders immediately
        self.render_every_n_frames = max(1, int(240 / render_fps))  # Render every N physics steps

        print(f"[CustomRenderer] Will render every {self.render_every_n_frames} frames (240Hz / {render_fps}fps)", flush=True)

        # Rendering state
        self.is_active = True

        print(f"[CustomRenderer] Initialized {window_width}x{window_height} @ {render_fps}fps")
        print(f"[CustomRenderer] Camera: distance={camera_distance}, yaw={camera_yaw}, pitch={camera_pitch}")
        print(f"[CustomRenderer] Controls: Left-drag to rotate, Right-click for coordinates, Mouse wheel to zoom")

    def _update_camera_matrices(self):
        """Update view and projection matrices based on camera parameters."""
        # Compute view matrix
        self.view_matrix = p.computeViewMatrixFromYawPitchRoll(
            cameraTargetPosition=self.camera_target,
            distance=self.camera_distance,
            yaw=self.camera_yaw,
            pitch=self.camera_pitch,
            roll=0,
            upAxisIndex=2,
            physicsClientId=self.client_id
        )

        # Compute projection matrix
        aspect = self.width / self.height
        self.proj_matrix = p.computeProjectionMatrixFOV(
            fov=60.0,
            aspect=aspect,
            nearVal=0.1,
            farVal=100.0,
            physicsClientId=self.client_id
        )

    def _mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events for camera control and coordinate picking."""

        # Left drag: rotate camera
        if event == cv2.EVENT_LBUTTONDOWN:
            self.mouse_pressed = True
            self.last_mouse_x = x
            self.last_mouse_y = y

        elif event == cv2.EVENT_LBUTTONUP:
            self.mouse_pressed = False

        elif event == cv2.EVENT_MOUSEMOVE and self.mouse_pressed:
            dx = x - self.last_mouse_x
            dy = y - self.last_mouse_y

            # Update camera angles
            self.camera_yaw += dx * 0.3
            self.camera_pitch -= dy * 0.3

            # Clamp pitch
            self.camera_pitch = max(-89, min(89, self.camera_pitch))

            self.last_mouse_x = x
            self.last_mouse_y = y

            self._update_camera_matrices()

        # Right click: get world coordinates
        elif event == cv2.EVENT_RBUTTONDOWN:
            coords = self._screen_to_world(x, y)
            if coords is not None:
                self.last_clicked_coords = coords
                print(f"\n[CustomRenderer] Clicked coordinates: ({coords[0]:.2f}, {coords[1]:.2f}, {coords[2]:.2f})")

        # Mouse wheel: zoom
        elif event == cv2.EVENT_MOUSEWHEEL:
            if flags > 0:  # Scroll up
                self.camera_distance = max(1.0, self.camera_distance - 0.5)
            else:  # Scroll down
                self.camera_distance = min(20.0, self.camera_distance + 0.5)

            self._update_camera_matrices()

    def _screen_to_world(self, screen_x: int, screen_y: int) -> Optional[Tuple[float, float, float]]:
        """
        Convert screen coordinates to 3D world coordinates via ray casting.

        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate

        Returns:
            World (x, y, z) coordinates or None if ray misses
        """
        # Normalize screen coordinates to [-1, 1]
        norm_x = (2.0 * screen_x / self.width) - 1.0
        norm_y = 1.0 - (2.0 * screen_y / self.height)

        # Compute ray from camera through screen point
        view_mat = np.array(self.view_matrix).reshape(4, 4, order='F')
        proj_mat = np.array(self.proj_matrix).reshape(4, 4, order='F')

        # Inverse projection
        clip_coords = np.array([norm_x, norm_y, -1.0, 1.0])
        eye_coords = np.linalg.inv(proj_mat) @ clip_coords
        eye_coords = np.array([eye_coords[0], eye_coords[1], -1.0, 0.0])

        # Inverse view
        world_coords = np.linalg.inv(view_mat) @ eye_coords
        ray_direction = world_coords[:3]
        ray_direction = ray_direction / np.linalg.norm(ray_direction)

        # Camera position
        camera_pos = np.linalg.inv(view_mat) @ np.array([0, 0, 0, 1])
        camera_pos = camera_pos[:3]

        # Ray cast to ground plane (z=0)
        # ray_point = camera_pos + t * ray_direction
        # Solve for t where z = 0
        if abs(ray_direction[2]) < 1e-6:
            return None

        t = -camera_pos[2] / ray_direction[2]
        if t < 0:
            return None

        intersection = camera_pos + t * ray_direction
        return (float(intersection[0]), float(intersection[1]), 0.0)

    def render(self) -> bool:
        """
        Render one frame to OpenCV window.

        Uses frame skipping to maintain target FPS without blocking.
        Call this every physics step - it will automatically skip frames as needed.

        Returns:
            True if window is still open, False if closed
        """
        # ALWAYS process input to keep window responsive
        try:
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord('q'):
                return False
        except Exception as e:
            print(f"[CustomRenderer] ERROR in waitKey: {e}", flush=True)
            return False

        # Frame skipping for performance - render every Nth frame
        self.render_skip_counter += 1
        should_render = (self.render_skip_counter >= self.render_every_n_frames)

        if not should_render:
            # Skip actual rendering but input was already processed
            return True

        # Reset counter and proceed with rendering
        self.render_skip_counter = 0
        current_time = time.time()

        if self.frame_count == 0:
            print(f"[CustomRenderer] Starting first render...", flush=True)

        # Get camera image from PyBullet (GPU-accelerated)
        try:
            if self.frame_count == 0:
                print(f"[CustomRenderer] Attempting first getCameraImage call...", flush=True)

            width, height, rgb_img, depth_img, seg_img = p.getCameraImage(
                width=self.width,
                height=self.height,
                viewMatrix=self.view_matrix,
                projectionMatrix=self.proj_matrix,
                renderer=p.ER_BULLET_HARDWARE_OPENGL,
                physicsClientId=self.client_id
            )

            if self.frame_count == 0:
                print(f"[CustomRenderer] SUCCESS! Got first image: {width}x{height}, rgb_img type: {type(rgb_img)}", flush=True)

        except Exception as e:
            print(f"[CustomRenderer] ERROR getting camera image: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

        # Convert to OpenCV format (RGB to BGR)
        rgb_array = np.array(rgb_img, dtype=np.uint8).reshape(height, width, 4)
        bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGBA2BGR)

        # Add FPS overlay
        self.frame_count += 1
        if current_time - self.fps_last_time >= 1.0:
            self.fps_counter = self.frame_count
            self.frame_count = 0
            self.fps_last_time = current_time

        # Draw HUD
        self._draw_hud(bgr_array)

        # Display frame
        try:
            if self.frame_count == 0:
                print(f"[CustomRenderer] Calling imshow for first time with image shape: {bgr_array.shape}", flush=True)
            cv2.imshow(self.window_name, bgr_array)
            if self.frame_count == 0:
                print(f"[CustomRenderer] First imshow successful!", flush=True)
        except Exception as e:
            print(f"[CustomRenderer] ERROR in imshow: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

        # R to reset camera (key was already checked at start of function)
        if key == ord('r'):
            self.camera_distance = 8.0
            self.camera_yaw = 50
            self.camera_pitch = -35
            self.camera_target = [0, 0, 0]
            self._update_camera_matrices()
            print("[CustomRenderer] Camera reset to default position")

        # Check if window was closed
        try:
            if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                return False
        except:
            return False

        self.last_render_time = current_time
        return True

    def _draw_hud(self, img: np.ndarray):
        """Draw heads-up display with info and controls."""
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        color = (0, 255, 0)  # Green
        bg_color = (0, 0, 0)  # Black

        # FPS counter
        fps_text = f"FPS: {self.fps_counter}"
        text_size = cv2.getTextSize(fps_text, font, font_scale, thickness)[0]
        cv2.rectangle(img, (10, 10), (20 + text_size[0], 40 + text_size[1]), bg_color, -1)
        cv2.putText(img, fps_text, (15, 35), font, font_scale, color, thickness)

        # Camera info
        cam_text = f"Cam: dist={self.camera_distance:.1f} yaw={self.camera_yaw:.0f} pitch={self.camera_pitch:.0f}"
        cv2.putText(img, cam_text, (15, 70), font, font_scale * 0.8, color, thickness - 1)

        # Controls
        controls = [
            "Controls:",
            "Left-drag: Rotate camera",
            "Right-click: Get coordinates",
            "Mouse wheel: Zoom in/out",
            "R: Reset camera",
            "Q/ESC: Quit"
        ]

        y_offset = self.height - 180
        for i, line in enumerate(controls):
            cv2.putText(img, line, (15, y_offset + i * 25), font, 0.5, color, 1)

        # Last clicked coordinates
        if self.last_clicked_coords is not None:
            x, y, z = self.last_clicked_coords
            coord_text = f"Last click: ({x:.2f}, {y:.2f}, {z:.2f})"
            cv2.putText(img, coord_text, (15, self.height - 20), font, 0.6, (0, 255, 255), 2)

    def get_last_clicked_coords(self) -> Optional[Tuple[float, float, float]]:
        """Get the last clicked world coordinates."""
        return self.last_clicked_coords

    def close(self):
        """Clean up renderer resources."""
        print("[CustomRenderer] Closing renderer")
        cv2.destroyWindow(self.window_name)
        cv2.destroyAllWindows()
        self.is_active = False
