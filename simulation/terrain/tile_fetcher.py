"""
Tile fetcher for Mapbox terrain and satellite imagery.

Handles:
- Converting lat/lng to tile coordinates
- Fetching terrain-rgb DEM tiles
- Decoding RGB values to elevation in meters
- Fetching and stitching satellite imagery
- Caching tiles locally
"""

import asyncio
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List
import io

import numpy as np

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .config import TerrainConfig


@dataclass
class BoundingBox:
    """Geographic bounding box."""
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float

    @property
    def center(self) -> Tuple[float, float]:
        """Get center point (lat, lng)."""
        return (
            (self.min_lat + self.max_lat) / 2,
            (self.min_lng + self.max_lng) / 2
        )

    @property
    def width_meters(self) -> float:
        """Approximate width in meters."""
        lat = (self.min_lat + self.max_lat) / 2
        return haversine_distance(lat, self.min_lng, lat, self.max_lng)

    @property
    def height_meters(self) -> float:
        """Approximate height in meters."""
        lng = (self.min_lng + self.max_lng) / 2
        return haversine_distance(self.min_lat, lng, self.max_lat, lng)


@dataclass
class TileCoord:
    """XYZ tile coordinates."""
    z: int
    x: int
    y: int


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in meters using Haversine formula."""
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def lat_lng_to_tile(lat: float, lng: float, zoom: int) -> TileCoord:
    """Convert latitude/longitude to tile coordinates at given zoom level."""
    n = 2 ** zoom
    x = int((lng + 180) / 360 * n)
    lat_rad = math.radians(lat)
    y = int((1 - math.asinh(math.tan(lat_rad)) / math.pi) / 2 * n)
    return TileCoord(z=zoom, x=x, y=y)


def tile_to_lat_lng(tile: TileCoord) -> Tuple[float, float, float, float]:
    """Convert tile coordinates to bounding box (north, south, east, west)."""
    n = 2 ** tile.z

    lng_west = tile.x / n * 360 - 180
    lng_east = (tile.x + 1) / n * 360 - 180

    lat_north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * tile.y / n))))
    lat_south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (tile.y + 1) / n))))

    return lat_north, lat_south, lng_east, lng_west


def get_tiles_for_bbox(bbox: BoundingBox, zoom: int) -> List[TileCoord]:
    """Get all tiles that cover a bounding box at given zoom level."""
    top_left = lat_lng_to_tile(bbox.max_lat, bbox.min_lng, zoom)
    bottom_right = lat_lng_to_tile(bbox.min_lat, bbox.max_lng, zoom)

    tiles = []
    for x in range(top_left.x, bottom_right.x + 1):
        for y in range(top_left.y, bottom_right.y + 1):
            tiles.append(TileCoord(z=zoom, x=x, y=y))

    return tiles


def bbox_from_center(lat: float, lng: float, size_meters: float) -> BoundingBox:
    """Create a bounding box centered on a point with given size in meters."""
    # Approximate degrees per meter at this latitude
    lat_per_meter = 1 / 111320  # ~111km per degree latitude
    lng_per_meter = 1 / (111320 * math.cos(math.radians(lat)))

    half_size = size_meters / 2

    return BoundingBox(
        min_lat=lat - half_size * lat_per_meter,
        max_lat=lat + half_size * lat_per_meter,
        min_lng=lng - half_size * lng_per_meter,
        max_lng=lng + half_size * lng_per_meter
    )


def decode_terrain_rgb(r: int, g: int, b: int) -> float:
    """
    Decode Mapbox terrain-rgb values to elevation in meters.

    Formula: height = -10000 + ((R * 256 * 256 + G * 256 + B) * 0.1)
    """
    return -10000 + ((r * 256 * 256 + g * 256 + b) * 0.1)


def decode_terrain_rgb_array(rgb_array: np.ndarray) -> np.ndarray:
    """
    Decode an entire RGB image array to elevation values.

    Args:
        rgb_array: numpy array of shape (height, width, 3) with RGB values

    Returns:
        numpy array of shape (height, width) with elevation in meters
    """
    r = rgb_array[:, :, 0].astype(np.float64)
    g = rgb_array[:, :, 1].astype(np.float64)
    b = rgb_array[:, :, 2].astype(np.float64)

    elevation = -10000 + ((r * 256 * 256 + g * 256 + b) * 0.1)
    return elevation


class TileFetcher:
    """Fetches and processes terrain and satellite tiles from Mapbox."""

    def __init__(self, config: TerrainConfig):
        self.config = config

        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp is required for tile fetching. Install with: pip install aiohttp")
        if not PIL_AVAILABLE:
            raise ImportError("Pillow is required for image processing. Install with: pip install Pillow")

    def _get_cache_path(self, url: str, suffix: str = '.png') -> Path:
        """Get cache file path for a URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return Path(self.config.cache_dir) / f"{url_hash}{suffix}"

    async def _fetch_tile(self, url: str, suffix: str = '.png') -> bytes:
        """Fetch a single tile, using cache if available."""
        if self.config.cache_enabled:
            cache_path = self._get_cache_path(url, suffix)
            if cache_path.exists():
                return cache_path.read_bytes()

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch tile: {response.status} - {url}")
                data = await response.read()

                if self.config.cache_enabled:
                    cache_path = self._get_cache_path(url, suffix)
                    cache_path.write_bytes(data)

                return data

    async def fetch_dem_tile(self, tile: TileCoord) -> np.ndarray:
        """
        Fetch a single DEM tile and decode to elevation array.

        Returns:
            numpy array of shape (tile_size, tile_size) with elevation in meters
        """
        url = self.config.get_dem_tile_url(tile.z, tile.x, tile.y)
        print(f"[TileFetcher] Fetching DEM tile z={tile.z} x={tile.x} y={tile.y}")
        data = await self._fetch_tile(url, '.png')

        img = Image.open(io.BytesIO(data))
        rgb_array = np.array(img)[:, :, :3]  # Ignore alpha if present

        # Debug: check RGB values
        print(f"[TileFetcher] DEM tile shape: {rgb_array.shape}, dtype: {rgb_array.dtype}")
        print(f"[TileFetcher] RGB sample (center pixel): R={rgb_array[128,128,0]}, G={rgb_array[128,128,1]}, B={rgb_array[128,128,2]}")
        print(f"[TileFetcher] RGB range: R=[{rgb_array[:,:,0].min()}-{rgb_array[:,:,0].max()}], G=[{rgb_array[:,:,1].min()}-{rgb_array[:,:,1].max()}], B=[{rgb_array[:,:,2].min()}-{rgb_array[:,:,2].max()}]")

        elevation = decode_terrain_rgb_array(rgb_array)
        print(f"[TileFetcher] Decoded elevation range: {elevation.min():.1f}m to {elevation.max():.1f}m")

        return elevation

    async def fetch_satellite_tile(self, tile: TileCoord) -> np.ndarray:
        """
        Fetch a single satellite imagery tile.

        Returns:
            numpy array of shape (tile_size, tile_size, 3) with RGB values
        """
        url = self.config.get_satellite_tile_url(tile.z, tile.x, tile.y)
        data = await self._fetch_tile(url, '.jpg')

        img = Image.open(io.BytesIO(data))
        return np.array(img)[:, :, :3]  # Ensure RGB only

    async def fetch_elevation_for_area(
        self,
        center_lat: float,
        center_lng: float,
        size_meters: float,
        zoom: Optional[int] = None,
        target_resolution: Optional[float] = None
    ) -> Tuple[np.ndarray, BoundingBox]:
        """
        Fetch elevation data for an area centered on a point.

        Args:
            center_lat: Center latitude
            center_lng: Center longitude
            size_meters: Size of area in meters (square)
            zoom: Optional zoom level (auto-calculated if not provided)
            target_resolution: Target meters per pixel (overrides config)

        Returns:
            Tuple of (elevation_array, actual_bounding_box)
        """
        bbox = bbox_from_center(center_lat, center_lng, size_meters)

        # Auto-calculate zoom level for good resolution
        if zoom is None:
            # Use configured or overridden target resolution
            target_meters_per_pixel = target_resolution or self.config.target_resolution
            zoom = self._calculate_optimal_zoom(bbox, target_meters_per_pixel)
            zoom = min(zoom, self.config.max_zoom)

        tiles = get_tiles_for_bbox(bbox, zoom)

        if len(tiles) == 0:
            raise ValueError("No tiles found for the specified area")

        # Fetch all tiles concurrently
        elevation_arrays = await asyncio.gather(*[
            self.fetch_dem_tile(tile) for tile in tiles
        ])

        # Stitch tiles together
        stitched = self._stitch_tiles(tiles, elevation_arrays, zoom)

        # Crop to exact bounding box
        cropped, actual_bbox = self._crop_to_bbox(stitched, tiles, bbox, zoom)

        return cropped, actual_bbox

    async def fetch_satellite_for_area(
        self,
        center_lat: float,
        center_lng: float,
        size_meters: float,
        zoom: Optional[int] = None,
        target_resolution: Optional[float] = None
    ) -> Tuple[np.ndarray, BoundingBox]:
        """
        Fetch satellite imagery for an area centered on a point.

        Args:
            center_lat: Center latitude
            center_lng: Center longitude
            size_meters: Size of area in meters (square)
            zoom: Optional zoom level (auto-calculated if not provided)
            target_resolution: Target meters per pixel (overrides config)

        Returns:
            Tuple of (rgb_array, actual_bounding_box)
        """
        bbox = bbox_from_center(center_lat, center_lng, size_meters)

        if zoom is None:
            target_meters_per_pixel = target_resolution or self.config.target_resolution
            zoom = self._calculate_optimal_zoom(bbox, target_meters_per_pixel)
            zoom = min(zoom, self.config.max_zoom)

        tiles = get_tiles_for_bbox(bbox, zoom)

        if len(tiles) == 0:
            raise ValueError("No tiles found for the specified area")

        # Fetch all tiles concurrently
        satellite_arrays = await asyncio.gather(*[
            self.fetch_satellite_tile(tile) for tile in tiles
        ])

        # Stitch tiles together
        stitched = self._stitch_tiles_rgb(tiles, satellite_arrays, zoom)

        # Crop to exact bounding box
        cropped, actual_bbox = self._crop_to_bbox_rgb(stitched, tiles, bbox, zoom)

        return cropped, actual_bbox

    def _calculate_optimal_zoom(self, bbox: BoundingBox, target_meters_per_pixel: float) -> int:
        """Calculate optimal zoom level for desired resolution."""
        # At zoom 0, Earth is 256 pixels wide (at equator ~157km per pixel)
        # Each zoom level doubles resolution
        equator_meters = 40075016.686
        base_meters_per_pixel = equator_meters / 512  # Using 512px tiles

        # Adjust for latitude
        lat = bbox.center[0]
        meters_per_pixel_at_equator = base_meters_per_pixel * math.cos(math.radians(lat))

        # Calculate zoom
        zoom = math.log2(meters_per_pixel_at_equator / target_meters_per_pixel)
        final_zoom = int(max(1, min(zoom, self.config.max_zoom)))
        print(f"[TileFetcher] Zoom calculation: target={target_meters_per_pixel}m/px -> zoom={final_zoom} (raw={zoom:.1f})")
        return final_zoom

    def _stitch_tiles(
        self,
        tiles: List[TileCoord],
        arrays: List[np.ndarray],
        zoom: int
    ) -> np.ndarray:
        """Stitch multiple elevation tile arrays into one."""
        if len(tiles) == 0:
            raise ValueError("No tiles to stitch")

        tile_size = arrays[0].shape[0]

        # Find tile grid bounds
        min_x = min(t.x for t in tiles)
        max_x = max(t.x for t in tiles)
        min_y = min(t.y for t in tiles)
        max_y = max(t.y for t in tiles)

        width = (max_x - min_x + 1) * tile_size
        height = (max_y - min_y + 1) * tile_size

        stitched = np.zeros((height, width), dtype=np.float64)

        for tile, arr in zip(tiles, arrays):
            x_offset = (tile.x - min_x) * tile_size
            y_offset = (tile.y - min_y) * tile_size
            stitched[y_offset:y_offset + tile_size, x_offset:x_offset + tile_size] = arr

        return stitched

    def _stitch_tiles_rgb(
        self,
        tiles: List[TileCoord],
        arrays: List[np.ndarray],
        zoom: int
    ) -> np.ndarray:
        """Stitch multiple RGB tile arrays into one."""
        if len(tiles) == 0:
            raise ValueError("No tiles to stitch")

        tile_size = arrays[0].shape[0]

        min_x = min(t.x for t in tiles)
        max_x = max(t.x for t in tiles)
        min_y = min(t.y for t in tiles)
        max_y = max(t.y for t in tiles)

        width = (max_x - min_x + 1) * tile_size
        height = (max_y - min_y + 1) * tile_size

        stitched = np.zeros((height, width, 3), dtype=np.uint8)

        for tile, arr in zip(tiles, arrays):
            x_offset = (tile.x - min_x) * tile_size
            y_offset = (tile.y - min_y) * tile_size
            stitched[y_offset:y_offset + tile_size, x_offset:x_offset + tile_size, :] = arr

        return stitched

    def _crop_to_bbox(
        self,
        stitched: np.ndarray,
        tiles: List[TileCoord],
        target_bbox: BoundingBox,
        zoom: int
    ) -> Tuple[np.ndarray, BoundingBox]:
        """Crop stitched array to target bounding box."""
        # Get the bounding box of the tile grid
        min_x = min(t.x for t in tiles)
        max_x = max(t.x for t in tiles)
        min_y = min(t.y for t in tiles)
        max_y = max(t.y for t in tiles)

        # Get geographic bounds of tile grid
        top_left_bounds = tile_to_lat_lng(TileCoord(zoom, min_x, min_y))
        bottom_right_bounds = tile_to_lat_lng(TileCoord(zoom, max_x, max_y))

        grid_bbox = BoundingBox(
            min_lat=bottom_right_bounds[1],
            max_lat=top_left_bounds[0],
            min_lng=top_left_bounds[3],
            max_lng=bottom_right_bounds[2]
        )

        # Calculate pixel coordinates for crop
        height, width = stitched.shape[:2]

        lat_range = grid_bbox.max_lat - grid_bbox.min_lat
        lng_range = grid_bbox.max_lng - grid_bbox.min_lng

        # Pixel coordinates (note: y is inverted - top of image is max lat)
        x1 = int((target_bbox.min_lng - grid_bbox.min_lng) / lng_range * width)
        x2 = int((target_bbox.max_lng - grid_bbox.min_lng) / lng_range * width)
        y1 = int((grid_bbox.max_lat - target_bbox.max_lat) / lat_range * height)
        y2 = int((grid_bbox.max_lat - target_bbox.min_lat) / lat_range * height)

        # Clamp to valid range
        x1 = max(0, min(x1, width - 1))
        x2 = max(0, min(x2, width))
        y1 = max(0, min(y1, height - 1))
        y2 = max(0, min(y2, height))

        cropped = stitched[y1:y2, x1:x2]

        return cropped, target_bbox

    def _crop_to_bbox_rgb(
        self,
        stitched: np.ndarray,
        tiles: List[TileCoord],
        target_bbox: BoundingBox,
        zoom: int
    ) -> Tuple[np.ndarray, BoundingBox]:
        """Crop stitched RGB array to target bounding box."""
        # Same logic as _crop_to_bbox but for 3-channel arrays
        min_x = min(t.x for t in tiles)
        max_x = max(t.x for t in tiles)
        min_y = min(t.y for t in tiles)
        max_y = max(t.y for t in tiles)

        top_left_bounds = tile_to_lat_lng(TileCoord(zoom, min_x, min_y))
        bottom_right_bounds = tile_to_lat_lng(TileCoord(zoom, max_x, max_y))

        grid_bbox = BoundingBox(
            min_lat=bottom_right_bounds[1],
            max_lat=top_left_bounds[0],
            min_lng=top_left_bounds[3],
            max_lng=bottom_right_bounds[2]
        )

        height, width = stitched.shape[:2]

        lat_range = grid_bbox.max_lat - grid_bbox.min_lat
        lng_range = grid_bbox.max_lng - grid_bbox.min_lng

        x1 = int((target_bbox.min_lng - grid_bbox.min_lng) / lng_range * width)
        x2 = int((target_bbox.max_lng - grid_bbox.min_lng) / lng_range * width)
        y1 = int((grid_bbox.max_lat - target_bbox.max_lat) / lat_range * height)
        y2 = int((grid_bbox.max_lat - target_bbox.min_lat) / lat_range * height)

        x1 = max(0, min(x1, width - 1))
        x2 = max(0, min(x2, width))
        y1 = max(0, min(y1, height - 1))
        y2 = max(0, min(y2, height))

        cropped = stitched[y1:y2, x1:x2, :]

        return cropped, target_bbox
