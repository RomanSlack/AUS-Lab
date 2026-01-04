"""
Terrain system for loading real-world elevation data and satellite imagery.

This module provides functionality to:
1. Fetch terrain elevation (DEM) tiles from Mapbox
2. Fetch satellite imagery tiles
3. Convert elevation data to 3D mesh geometry
4. Handle coordinate transformations between geographic and local coordinates
"""

from .config import TerrainConfig
from .tile_fetcher import TileFetcher
from .mesh_generator import TerrainMeshGenerator
from .terrain_service import TerrainService

__all__ = [
    'TerrainConfig',
    'TileFetcher',
    'TerrainMeshGenerator',
    'TerrainService',
]
