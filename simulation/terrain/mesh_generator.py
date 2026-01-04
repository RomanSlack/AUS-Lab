"""
Mesh generator for converting elevation data to 3D geometry.

Generates:
- Vertices (positions)
- Normals (for lighting)
- UVs (for texture mapping)
- Indices (for triangles)

Output is designed for direct use with Three.js BufferGeometry.
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional
import base64


@dataclass
class TerrainMeshData:
    """
    Container for terrain mesh geometry data.

    All arrays are flattened for efficient transfer to frontend.
    """
    # Geometry data (flattened)
    positions: np.ndarray    # Float32, shape (n_vertices * 3,)
    normals: np.ndarray      # Float32, shape (n_vertices * 3,)
    uvs: np.ndarray          # Float32, shape (n_vertices * 2,)
    indices: np.ndarray      # Uint32, shape (n_triangles * 3,)

    # Metadata
    width: int               # Number of vertices in X direction
    height: int              # Number of vertices in Y direction
    min_elevation: float     # Minimum elevation in source data (meters)
    max_elevation: float     # Maximum elevation in source data (meters)

    # Mesh bounds (in simulation coordinates)
    bounds_min: Tuple[float, float, float]  # (x, y, z)
    bounds_max: Tuple[float, float, float]  # (x, y, z)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'positions': base64.b64encode(self.positions.astype(np.float32).tobytes()).decode('ascii'),
            'normals': base64.b64encode(self.normals.astype(np.float32).tobytes()).decode('ascii'),
            'uvs': base64.b64encode(self.uvs.astype(np.float32).tobytes()).decode('ascii'),
            'indices': base64.b64encode(self.indices.astype(np.uint32).tobytes()).decode('ascii'),
            'width': self.width,
            'height': self.height,
            'minElevation': self.min_elevation,
            'maxElevation': self.max_elevation,
            'boundsMin': list(self.bounds_min),
            'boundsMax': list(self.bounds_max),
            'vertexCount': len(self.positions) // 3,
            'indexCount': len(self.indices),
        }


class TerrainMeshGenerator:
    """
    Generates 3D mesh geometry from elevation data.

    Converts a 2D elevation array into a triangulated mesh suitable
    for rendering in Three.js.
    """

    def __init__(
        self,
        target_resolution: int = 256,
        elevation_scale: float = 1.0,
        scale_factor: float = 0.01
    ):
        """
        Initialize mesh generator.

        Args:
            target_resolution: Target number of vertices per side (will resample if needed)
            elevation_scale: Vertical exaggeration factor (1.0 = realistic)
            scale_factor: Scale factor to convert real meters to simulation units
                         e.g., 0.01 means 1000m real = 10m simulation
        """
        self.target_resolution = target_resolution
        self.elevation_scale = elevation_scale
        self.scale_factor = scale_factor

    def generate(
        self,
        elevation: np.ndarray,
        real_width_meters: float,
        real_height_meters: float,
        center_offset: Tuple[float, float] = (0.0, 0.0)
    ) -> TerrainMeshData:
        """
        Generate mesh from elevation data.

        Args:
            elevation: 2D numpy array of elevation values in meters
            real_width_meters: Real-world width of the area in meters
            real_height_meters: Real-world height of the area in meters
            center_offset: Offset to apply to center the mesh (x, y)

        Returns:
            TerrainMeshData with all geometry arrays
        """
        # Resample elevation to target resolution if needed
        if elevation.shape[0] != self.target_resolution or elevation.shape[1] != self.target_resolution:
            elevation = self._resample(elevation, self.target_resolution, self.target_resolution)

        height_px, width_px = elevation.shape

        # Calculate scaled dimensions
        sim_width = real_width_meters * self.scale_factor
        sim_height = real_height_meters * self.scale_factor

        # Get elevation statistics
        min_elev = float(np.min(elevation))
        max_elev = float(np.max(elevation))

        # Normalize elevation relative to minimum (so lowest point is at y=0)
        # Then scale to simulation units
        elevation_normalized = (elevation - min_elev) * self.scale_factor * self.elevation_scale

        # Generate vertices
        positions, uvs = self._generate_vertices(
            elevation_normalized,
            sim_width,
            sim_height,
            center_offset
        )

        # Generate indices for triangle mesh
        indices = self._generate_indices(width_px, height_px)

        # Calculate normals from geometry
        normals = self._calculate_normals(positions, indices, width_px, height_px)

        # Calculate bounds
        positions_reshaped = positions.reshape(-1, 3)
        bounds_min = (
            float(np.min(positions_reshaped[:, 0])),
            float(np.min(positions_reshaped[:, 1])),
            float(np.min(positions_reshaped[:, 2]))
        )
        bounds_max = (
            float(np.max(positions_reshaped[:, 0])),
            float(np.max(positions_reshaped[:, 1])),
            float(np.max(positions_reshaped[:, 2]))
        )

        return TerrainMeshData(
            positions=positions,
            normals=normals,
            uvs=uvs,
            indices=indices,
            width=width_px,
            height=height_px,
            min_elevation=min_elev,
            max_elevation=max_elev,
            bounds_min=bounds_min,
            bounds_max=bounds_max
        )

    def _resample(self, array: np.ndarray, new_height: int, new_width: int) -> np.ndarray:
        """Resample array to new dimensions using bilinear interpolation."""
        from scipy import ndimage
        zoom_factors = (new_height / array.shape[0], new_width / array.shape[1])
        return ndimage.zoom(array, zoom_factors, order=1)

    def _generate_vertices(
        self,
        elevation: np.ndarray,
        width: float,
        height: float,
        center_offset: Tuple[float, float]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate vertex positions and UV coordinates.

        Three.js coordinate system:
        - X: right
        - Y: up (height/elevation)
        - Z: towards camera (we use -Z for forward/north)

        The mesh is centered at origin with Y as the up axis.
        """
        h, w = elevation.shape

        # Create coordinate grids
        # X goes from -width/2 to +width/2
        # Z goes from -height/2 to +height/2 (note: Z is horizontal in Three.js)
        x_coords = np.linspace(-width / 2, width / 2, w) + center_offset[0]
        z_coords = np.linspace(-height / 2, height / 2, h) + center_offset[1]

        # Create mesh grids
        x_grid, z_grid = np.meshgrid(x_coords, z_coords)

        # Y is elevation (up direction in Three.js)
        y_grid = elevation

        # Flatten and interleave: [x0, y0, z0, x1, y1, z1, ...]
        positions = np.column_stack([
            x_grid.flatten(),
            y_grid.flatten(),
            z_grid.flatten()
        ]).flatten().astype(np.float32)

        # UV coordinates (0 to 1)
        u_coords = np.linspace(0, 1, w)
        v_coords = np.linspace(0, 1, h)
        u_grid, v_grid = np.meshgrid(u_coords, v_coords)

        # Flip V coordinate (images have origin at top-left, UVs at bottom-left)
        v_grid = 1.0 - v_grid

        uvs = np.column_stack([
            u_grid.flatten(),
            v_grid.flatten()
        ]).flatten().astype(np.float32)

        return positions, uvs

    def _generate_indices(self, width: int, height: int) -> np.ndarray:
        """
        Generate triangle indices for a grid mesh.

        Creates two triangles per grid cell:
        a---b
        |  /|
        | / |
        |/  |
        c---d
        Triangle 1: a, c, b
        Triangle 2: b, c, d
        """
        indices = []

        for y in range(height - 1):
            for x in range(width - 1):
                # Vertex indices
                a = y * width + x
                b = y * width + (x + 1)
                c = (y + 1) * width + x
                d = (y + 1) * width + (x + 1)

                # Two triangles per cell
                # Counter-clockwise winding for front face
                indices.extend([a, c, b])  # Triangle 1
                indices.extend([b, c, d])  # Triangle 2

        return np.array(indices, dtype=np.uint32)

    def _calculate_normals(
        self,
        positions: np.ndarray,
        indices: np.ndarray,
        width: int,
        height: int
    ) -> np.ndarray:
        """
        Calculate vertex normals from geometry.

        Uses the gradient method for terrain - faster and smoother than
        per-triangle normal calculation.
        """
        # Reshape positions to 2D grid of 3D points
        pos_grid = positions.reshape(height, width, 3)

        # Extract Y (elevation) values
        elevations = pos_grid[:, :, 1]

        # Calculate cell size from positions
        cell_size_x = (pos_grid[0, -1, 0] - pos_grid[0, 0, 0]) / (width - 1) if width > 1 else 1.0
        cell_size_z = (pos_grid[-1, 0, 2] - pos_grid[0, 0, 2]) / (height - 1) if height > 1 else 1.0

        # Calculate gradients
        dy_dx = np.gradient(elevations, cell_size_x, axis=1)
        dy_dz = np.gradient(elevations, cell_size_z, axis=0)

        # Normal = (-dY/dX, 1, -dY/dZ) normalized
        # This points "up" for flat terrain and tilts with slopes
        normals_x = -dy_dx
        normals_y = np.ones_like(elevations)
        normals_z = -dy_dz

        # Normalize
        length = np.sqrt(normals_x**2 + normals_y**2 + normals_z**2)
        length = np.maximum(length, 1e-8)  # Avoid division by zero

        normals_x /= length
        normals_y /= length
        normals_z /= length

        # Flatten and interleave
        normals = np.column_stack([
            normals_x.flatten(),
            normals_y.flatten(),
            normals_z.flatten()
        ]).flatten().astype(np.float32)

        return normals


def generate_test_terrain(size: int = 64) -> TerrainMeshData:
    """
    Generate a test terrain with procedural hills.

    Useful for testing without Mapbox API.
    """
    # Create procedural elevation
    x = np.linspace(0, 4 * np.pi, size)
    z = np.linspace(0, 4 * np.pi, size)
    x_grid, z_grid = np.meshgrid(x, z)

    # Combine multiple frequencies for natural-looking terrain
    elevation = (
        500 * np.sin(x_grid * 0.3) * np.cos(z_grid * 0.3) +
        200 * np.sin(x_grid * 0.7 + 1) * np.sin(z_grid * 0.5) +
        100 * np.sin(x_grid * 1.3) * np.cos(z_grid * 1.1 + 2) +
        50 * np.sin(x_grid * 2.5 + 3) * np.sin(z_grid * 2.3)
    )

    # Shift to positive values (simulating real terrain)
    elevation = elevation - elevation.min() + 100  # Minimum 100m

    generator = TerrainMeshGenerator(
        target_resolution=size,
        elevation_scale=1.0,
        scale_factor=0.01
    )

    return generator.generate(
        elevation,
        real_width_meters=2000,  # 2km wide
        real_height_meters=2000   # 2km deep
    )
