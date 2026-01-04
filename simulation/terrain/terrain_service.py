"""
Main terrain service that orchestrates tile fetching and mesh generation.

Provides a simple interface for loading terrain from coordinates.
"""

import asyncio
import base64
import io
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
import numpy as np

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .config import TerrainConfig, load_config
from .tile_fetcher import TileFetcher, BoundingBox
from .mesh_generator import TerrainMeshGenerator, TerrainMeshData


@dataclass
class TerrainLoadResult:
    """Result of loading terrain for an area."""

    # Mesh geometry
    mesh: TerrainMeshData

    # Satellite texture as base64 JPEG
    texture_base64: str
    texture_width: int
    texture_height: int

    # Geographic metadata
    center_lat: float
    center_lng: float
    area_size_meters: float

    # Coordinate mapping info
    # Maps simulation coords to geographic coords
    geo_origin_lat: float  # Lat at simulation (0, 0)
    geo_origin_lng: float  # Lng at simulation (0, 0)
    meters_per_unit: float  # How many real meters per simulation unit

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'mesh': self.mesh.to_dict(),
            'texture': {
                'data': self.texture_base64,
                'width': self.texture_width,
                'height': self.texture_height,
            },
            'location': {
                'centerLat': self.center_lat,
                'centerLng': self.center_lng,
                'areaSizeMeters': self.area_size_meters,
            },
            'coordinateMapping': {
                'geoOriginLat': self.geo_origin_lat,
                'geoOriginLng': self.geo_origin_lng,
                'metersPerUnit': self.meters_per_unit,
            }
        }


class TerrainService:
    """
    High-level service for loading real-world terrain.

    Example usage:
        service = TerrainService()
        result = await service.load_terrain(
            lat=39.0968,  # Lake Tahoe
            lng=-120.0324,
            size_meters=2000
        )
    """

    def __init__(self, config: Optional[TerrainConfig] = None):
        """
        Initialize terrain service.

        Args:
            config: Optional configuration. If not provided, loads from environment.
        """
        self.config = config or load_config()
        self._fetcher: Optional[TileFetcher] = None
        self._generator: Optional[TerrainMeshGenerator] = None

    @property
    def is_configured(self) -> bool:
        """Check if service is properly configured with API keys."""
        return self.config.is_configured

    def _ensure_initialized(self):
        """Lazily initialize components."""
        if self._fetcher is None:
            self._fetcher = TileFetcher(self.config)
        if self._generator is None:
            self._generator = TerrainMeshGenerator(
                target_resolution=self.config.mesh_resolution,
                elevation_scale=self.config.elevation_scale,
                scale_factor=self.config.scale_factor
            )

    async def load_terrain(
        self,
        lat: float,
        lng: float,
        size_meters: float = 2000.0,
        zoom: Optional[int] = None,
        realistic_scale: bool = False,
        target_resolution: Optional[float] = None
    ) -> TerrainLoadResult:
        """
        Load terrain for a geographic location.

        Args:
            lat: Center latitude
            lng: Center longitude
            size_meters: Size of area to load in meters (square)
            zoom: Optional zoom level (auto-calculated if not provided)
            realistic_scale: If True, use 1:1 scale (1m real = 1m simulation)
            target_resolution: Target meters per pixel for imagery (lower = higher res)

        Returns:
            TerrainLoadResult with mesh geometry and satellite texture

        Raises:
            ValueError: If not configured or invalid parameters
            Exception: If tile fetching fails
        """
        if not self.is_configured:
            raise ValueError(
                "Terrain service not configured. Set MAPBOX_ACCESS_TOKEN environment variable "
                "or create a .env file with MAPBOX_ACCESS_TOKEN=your_token"
            )

        self._ensure_initialized()

        # Determine scale factor
        if realistic_scale:
            scale_factor = 1.0  # 1:1 scale
        else:
            scale_factor = self.config.scale_factor

        # Update generator's scale factor
        self._generator.scale_factor = scale_factor

        # Fetch elevation and satellite data concurrently
        elevation_task = self._fetcher.fetch_elevation_for_area(
            lat, lng, size_meters, zoom, target_resolution
        )
        satellite_task = self._fetcher.fetch_satellite_for_area(
            lat, lng, size_meters, zoom, target_resolution
        )

        (elevation, elev_bbox), (satellite, sat_bbox) = await asyncio.gather(
            elevation_task,
            satellite_task
        )

        # Calculate real dimensions from bounding box
        real_width = elev_bbox.width_meters
        real_height = elev_bbox.height_meters

        # Generate mesh
        mesh = self._generator.generate(
            elevation,
            real_width_meters=real_width,
            real_height_meters=real_height,
            center_offset=(0.0, 0.0)
        )

        # Encode satellite image as base64 JPEG (higher quality for high-res)
        jpeg_quality = 90 if target_resolution and target_resolution < 1.5 else 85
        texture_base64 = self._encode_texture(satellite, quality=jpeg_quality)

        # Calculate coordinate mapping
        meters_per_unit = 1.0 / scale_factor

        return TerrainLoadResult(
            mesh=mesh,
            texture_base64=texture_base64,
            texture_width=satellite.shape[1],
            texture_height=satellite.shape[0],
            center_lat=lat,
            center_lng=lng,
            area_size_meters=size_meters,
            geo_origin_lat=lat,
            geo_origin_lng=lng,
            meters_per_unit=meters_per_unit
        )

    def _encode_texture(self, rgb_array: np.ndarray, quality: int = 85) -> str:
        """Encode RGB array as base64 JPEG."""
        if not PIL_AVAILABLE:
            raise ImportError("Pillow required for texture encoding")

        img = Image.fromarray(rgb_array.astype(np.uint8))

        # Resize if too large (limit to 2048px for WebGL)
        max_size = 2048
        if img.width > max_size or img.height > max_size:
            ratio = min(max_size / img.width, max_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality)
        return base64.b64encode(buffer.getvalue()).decode('ascii')

    async def get_elevation_at_point(self, lat: float, lng: float) -> float:
        """
        Get elevation at a specific point.

        Useful for placing drones at correct altitude.
        """
        if not self.is_configured:
            raise ValueError("Terrain service not configured")

        self._ensure_initialized()

        # Fetch small area around point
        elevation, _ = await self._fetcher.fetch_elevation_for_area(
            lat, lng, 100, zoom=14  # Small area, high detail
        )

        # Return center value
        h, w = elevation.shape
        return float(elevation[h // 2, w // 2])


# Singleton instance for use in FastAPI
_terrain_service: Optional[TerrainService] = None


def get_terrain_service() -> TerrainService:
    """Get the global terrain service instance."""
    global _terrain_service
    if _terrain_service is None:
        _terrain_service = TerrainService()
    return _terrain_service


# Convenience function for running from sync code
def load_terrain_sync(
    lat: float,
    lng: float,
    size_meters: float = 2000.0
) -> TerrainLoadResult:
    """Synchronous wrapper for load_terrain."""
    service = get_terrain_service()
    return asyncio.run(service.load_terrain(lat, lng, size_meters))
