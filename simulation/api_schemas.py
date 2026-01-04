"""
Pydantic models for API request/response validation.
"""

from typing import List, Union, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


class SpawnRequest(BaseModel):
    """Request to spawn or respawn swarm with N drones."""
    num: int = Field(default=5, ge=1, le=50, description="Number of drones to spawn")


class TakeoffRequest(BaseModel):
    """Request to takeoff drones to specified altitude."""
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {"ids": ["all"], "altitude": 1.5},
            {"ids": [0, 1, 2], "altitude": 2.0}
        ]
    })

    ids: Union[List[int], List[Literal["all"]]] = Field(
        default=["all"],
        description="List of drone IDs or ['all'] for all drones"
    )
    altitude: float = Field(default=1.0, ge=0.1, le=5.0, description="Target altitude in meters")

    @field_validator('ids')
    @classmethod
    def validate_ids(cls, v):
        if isinstance(v, list) and len(v) == 1 and v[0] == "all":
            return v
        if isinstance(v, list) and all(isinstance(i, int) for i in v):
            return v
        raise ValueError("ids must be ['all'] or a list of integers")


class LandRequest(BaseModel):
    """Request to land drones."""
    ids: Union[List[int], List[Literal["all"]]] = Field(
        default=["all"],
        description="List of drone IDs or ['all'] for all drones"
    )

    @field_validator('ids')
    @classmethod
    def validate_ids(cls, v):
        if isinstance(v, list) and len(v) == 1 and v[0] == "all":
            return v
        if isinstance(v, list) and all(isinstance(i, int) for i in v):
            return v
        raise ValueError("ids must be ['all'] or a list of integers")


class HoverRequest(BaseModel):
    """Request to hover drones at current position."""
    ids: Union[List[int], List[Literal["all"]]] = Field(
        default=["all"],
        description="List of drone IDs or ['all'] for all drones"
    )

    @field_validator('ids')
    @classmethod
    def validate_ids(cls, v):
        if isinstance(v, list) and len(v) == 1 and v[0] == "all":
            return v
        if isinstance(v, list) and all(isinstance(i, int) for i in v):
            return v
        raise ValueError("ids must be ['all'] or a list of integers")


class GotoRequest(BaseModel):
    """Request to move a single drone to target position."""
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {"id": 0, "x": 2.0, "y": 1.0, "z": 1.5, "yaw": 0.0},
            {"id": 1, "x": -1.5, "y": 2.0, "z": 2.0, "yaw": 1.57}
        ]
    })

    id: int = Field(ge=0, description="Drone ID")
    x: float = Field(description="Target X position in meters")
    y: float = Field(description="Target Y position in meters")
    z: float = Field(ge=0.1, le=5.0, description="Target Z position (altitude) in meters")
    yaw: float = Field(default=0.0, description="Target yaw angle in radians")

    @field_validator('x', 'y')
    @classmethod
    def validate_xy(cls, v):
        if abs(v) > 10.0:
            raise ValueError("x and y must be within ±10.0 meters")
        return v


class VelocityRequest(BaseModel):
    """Request to set drone velocity."""
    id: int = Field(ge=0, description="Drone ID")
    vx: float = Field(description="X velocity in m/s")
    vy: float = Field(description="Y velocity in m/s")
    vz: float = Field(description="Z velocity in m/s")
    yaw_rate: float = Field(default=0.0, description="Yaw rate in rad/s")

    @field_validator('vx', 'vy', 'vz')
    @classmethod
    def validate_velocity(cls, v):
        if abs(v) > 5.0:
            raise ValueError("Velocity components must be within ±5.0 m/s")
        return v

    @field_validator('yaw_rate')
    @classmethod
    def validate_yaw_rate(cls, v):
        if abs(v) > 2 * 3.14159:
            raise ValueError("Yaw rate must be within ±2π rad/s")
        return v


class FormationRequest(BaseModel):
    """Request to arrange swarm in formation."""
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {"pattern": "circle", "center": [0, 0, 2.0], "radius": 2.0},
            {"pattern": "line", "center": [0, 0, 1.5], "spacing": 1.0, "axis": "x"},
            {"pattern": "grid", "center": [0, 0, 1.5], "spacing": 0.8},
            {"pattern": "v", "center": [0, 0, 1.5], "spacing": 0.7}
        ]
    })

    pattern: Literal["line", "circle", "grid", "v"] = Field(
        description="Formation pattern: line, circle, grid, or v"
    )
    center: List[float] = Field(
        default=[0.0, 0.0, 1.0],
        min_length=3,
        max_length=3,
        description="Formation center [x, y, z]"
    )
    spacing: float = Field(default=1.0, ge=0.5, le=3.0, description="Spacing between drones in meters")
    radius: float = Field(default=1.5, ge=0.5, le=5.0, description="Radius for circular formation")
    axis: Literal["x", "y"] = Field(default="x", description="Axis for line formation")

    @field_validator('center')
    @classmethod
    def validate_center(cls, v):
        if abs(v[0]) > 10.0 or abs(v[1]) > 10.0:
            raise ValueError("Center x,y must be within ±10.0 meters")
        if v[2] < 0.1 or v[2] > 5.0:
            raise ValueError("Center z must be between 0.1 and 5.0 meters")
        return v


class DroneState(BaseModel):
    """State information for a single drone."""
    id: int
    pos: List[float] = Field(description="Position [x, y, z] in meters")
    vel: List[float] = Field(description="Velocity [vx, vy, vz] in m/s")
    yaw: float = Field(description="Yaw angle in radians")
    battery: float = Field(ge=0.0, le=100.0, description="Battery percentage")
    healthy: bool = Field(description="Health status flag")


class StateResponse(BaseModel):
    """Response containing all drone states."""
    drones: List[DroneState]
    timestamp: float = Field(description="Simulation time in seconds")


class CommandResponse(BaseModel):
    """Generic response for command execution."""
    success: bool
    message: str
    affected_drones: List[int] = Field(default_factory=list)


class ResetResponse(BaseModel):
    """Response for reset command."""
    success: bool
    message: str
    num_drones: int


class ClickCoordsResponse(BaseModel):
    """Response containing last clicked coordinates."""
    has_click: bool = Field(description="Whether a click has been registered")
    coords: List[float] = Field(default_factory=list, description="[x, y, z] coordinates if clicked")
    message: str


class HivemindMoveRequest(BaseModel):
    """Request to move the hivemind."""
    position: List[float] = Field(default=[0.0, 0.0, 1.0], min_length=3, max_length=3, description="Target center of the swarm")
    yaw: float = Field(default=0.0, description="Target yaw of the swarm")
    scale: float = Field(default=1.0, ge=0.1, le=5.0, description="Target scale of the swarm")


# ============================================================================
# Terrain System Schemas
# ============================================================================

class TerrainLoadRequest(BaseModel):
    """Request to load terrain for a geographic location."""
    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {"lat": 39.0968, "lng": -120.0324, "size_meters": 2000},  # Lake Tahoe
            {"lat": 36.1069, "lng": -112.1129, "size_meters": 5000, "realistic_scale": True},  # Grand Canyon 1:1
            {"lat": 46.8523, "lng": -121.7603, "size_meters": 3000, "resolution": "high"},  # Mt Rainier HD
        ]
    })

    lat: float = Field(description="Center latitude (-90 to 90)")
    lng: float = Field(description="Center longitude (-180 to 180)")
    size_meters: float = Field(
        default=2000.0,
        ge=100.0,
        le=10000.0,
        description="Size of area to load in meters (100-10000)"
    )
    zoom: int = Field(
        default=None,
        ge=1,
        le=15,
        description="Optional zoom level (1-15). Auto-calculated if not provided."
    )
    realistic_scale: bool = Field(
        default=False,
        description="Use 1:1 scale (1m real = 1m simulation). Drones will appear at realistic size relative to terrain."
    )
    resolution: Literal["low", "medium", "high", "ultra"] = Field(
        default="medium",
        description="Satellite imagery resolution: low (~4m/px), medium (~2m/px), high (~1m/px), ultra (~0.5m/px)"
    )

    @field_validator('lat')
    @classmethod
    def validate_lat(cls, v):
        if v < -90 or v > 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator('lng')
    @classmethod
    def validate_lng(cls, v):
        if v < -180 or v > 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v


class TerrainMeshResponse(BaseModel):
    """Mesh geometry data for terrain."""
    positions: str = Field(description="Base64-encoded Float32 array of vertex positions")
    normals: str = Field(description="Base64-encoded Float32 array of vertex normals")
    uvs: str = Field(description="Base64-encoded Float32 array of UV coordinates")
    indices: str = Field(description="Base64-encoded Uint32 array of triangle indices")
    width: int = Field(description="Number of vertices in X direction")
    height: int = Field(description="Number of vertices in Y direction")
    minElevation: float = Field(description="Minimum elevation in source data (meters)")
    maxElevation: float = Field(description="Maximum elevation in source data (meters)")
    boundsMin: List[float] = Field(description="Mesh bounds minimum [x, y, z]")
    boundsMax: List[float] = Field(description="Mesh bounds maximum [x, y, z]")
    vertexCount: int = Field(description="Total number of vertices")
    indexCount: int = Field(description="Total number of indices")


class TerrainTextureResponse(BaseModel):
    """Satellite texture data."""
    data: str = Field(description="Base64-encoded JPEG image data")
    width: int = Field(description="Texture width in pixels")
    height: int = Field(description="Texture height in pixels")


class TerrainLocationResponse(BaseModel):
    """Geographic location info."""
    centerLat: float = Field(description="Center latitude")
    centerLng: float = Field(description="Center longitude")
    areaSizeMeters: float = Field(description="Area size in meters")


class TerrainCoordinateMappingResponse(BaseModel):
    """Coordinate mapping between simulation and geographic coordinates."""
    geoOriginLat: float = Field(description="Geographic latitude at simulation origin")
    geoOriginLng: float = Field(description="Geographic longitude at simulation origin")
    metersPerUnit: float = Field(description="Real-world meters per simulation unit")


class TerrainLoadResponse(BaseModel):
    """Complete response for terrain load request."""
    success: bool = Field(description="Whether terrain was loaded successfully")
    mesh: TerrainMeshResponse = Field(description="Mesh geometry data")
    texture: TerrainTextureResponse = Field(description="Satellite texture data")
    location: TerrainLocationResponse = Field(description="Geographic location info")
    coordinateMapping: TerrainCoordinateMappingResponse = Field(description="Coordinate mapping info")


class TerrainStatusResponse(BaseModel):
    """Status of terrain service."""
    configured: bool = Field(description="Whether terrain service is configured with API keys")
    cacheEnabled: bool = Field(description="Whether tile caching is enabled")
    cacheDir: str = Field(description="Cache directory path")
    message: str = Field(description="Status message")
