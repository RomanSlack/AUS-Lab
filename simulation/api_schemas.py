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
