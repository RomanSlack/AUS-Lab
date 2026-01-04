"""
Configuration for terrain services.

Supports loading Mapbox API key from environment variables or .env file.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class TerrainConfig:
    """Configuration for terrain loading and generation."""

    # Mapbox API key (required for fetching tiles)
    mapbox_access_token: str = field(default_factory=lambda: os.getenv('MAPBOX_ACCESS_TOKEN', ''))

    # Tile settings
    tile_size: int = 512  # Pixels per tile (256 or 512)
    max_zoom: int = 15    # Maximum zoom level for terrain (increased from 14)

    # Mesh generation settings
    mesh_resolution: int = 512  # Vertices per side (increased from 256 for better detail)
    elevation_scale: float = 1.0  # Vertical exaggeration factor

    # Default area settings (in meters)
    default_area_size: float = 2000.0  # 2km x 2km default area

    # Simulation scale factor
    # Real-world terrain is huge, we scale it down to fit drone simulation bounds
    # e.g., scale_factor=0.01 means 1000m real = 10m simulation
    # For realistic 1:1 scale, set to 1.0
    scale_factor: float = 0.01

    # Realistic scale mode (1:1 scale where 1m real = 1m simulation)
    # When True, scale_factor is set to 1.0 and physics bounds are expanded
    realistic_scale: bool = False

    # Target meters per pixel for satellite imagery
    # Lower = higher resolution, but more tiles to fetch
    # 1.0 = ~1m per pixel (high detail)
    # 2.0 = ~2m per pixel (medium detail, faster)
    # 0.5 = ~0.5m per pixel (very high detail, slow)
    target_resolution: float = 1.0

    # Cache settings
    cache_enabled: bool = True
    cache_dir: str = field(default_factory=lambda: str(Path.home() / '.aus-lab' / 'terrain_cache'))

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.mapbox_access_token:
            # Try loading from .env file in project root
            self._load_from_dotenv()

        # Create cache directory if enabled
        if self.cache_enabled:
            Path(self.cache_dir).mkdir(parents=True, exist_ok=True)

    def _load_from_dotenv(self):
        """Attempt to load API key from .env file."""
        env_paths = [
            Path(__file__).parent.parent.parent / '.env',  # Project root
            Path.cwd() / '.env',
        ]

        for env_path in env_paths:
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('MAPBOX_ACCESS_TOKEN='):
                            self.mapbox_access_token = line.split('=', 1)[1].strip().strip('"\'')
                            return

    @property
    def is_configured(self) -> bool:
        """Check if the terrain service is properly configured."""
        return bool(self.mapbox_access_token)

    def get_dem_tile_url(self, z: int, x: int, y: int) -> str:
        """Get URL for a terrain-rgb DEM tile."""
        # Note: Don't use @2x for terrain-rgb - it's a data tile, not visual
        # The pngraw format gives us raw PNG without any re-encoding
        return (
            f"https://api.mapbox.com/v4/mapbox.terrain-rgb/"
            f"{z}/{x}/{y}.pngraw?access_token={self.mapbox_access_token}"
        )

    def get_satellite_tile_url(self, z: int, x: int, y: int) -> str:
        """Get URL for a satellite imagery tile."""
        return (
            f"https://api.mapbox.com/v4/mapbox.satellite/"
            f"{z}/{x}/{y}@2x.jpg90?access_token={self.mapbox_access_token}"
        )


def load_config() -> TerrainConfig:
    """Load terrain configuration from environment."""
    return TerrainConfig()
