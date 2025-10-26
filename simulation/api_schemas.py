"""
Pydantic models for API request/response validation.
"""

from typing import List, Union, Literal
from pydantic import BaseModel, Field, field_validator


class SpawnRequest(BaseModel):
    """Request to spawn or respawn swarm with N drones."""
    num: int = Field(default=5, ge=1, le=50, description="Number of drones to spawn")


class TakeoffRequest(BaseModel):
    """Request to takeoff drones to specified altitude."""
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
