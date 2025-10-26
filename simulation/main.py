"""
Main entrypoint for UAV swarm simulation with HTTP API.
Launches both the simulation loop and FastAPI server in the same process.
"""

import argparse
import asyncio
import os
import signal
import sys
import threading
from contextlib import asynccontextmanager

# Fix for hybrid Intel/NVIDIA systems: Force NVIDIA GPU for PyBullet GUI
# This resolves "Failed to retrieve a framebuffer config" errors on Ubuntu 24.04
# Must be set BEFORE importing pybullet
os.environ['__NV_PRIME_RENDER_OFFLOAD'] = '1'
os.environ['__GLX_VENDOR_LIBRARY_NAME'] = 'nvidia'

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from swarm import SwarmWorld, DroneCommand
from api_schemas import (
    SpawnRequest, TakeoffRequest, LandRequest, HoverRequest,
    GotoRequest, VelocityRequest, FormationRequest,
    StateResponse, CommandResponse, ResetResponse
)


# Global swarm instance
swarm: SwarmWorld = None
sim_thread: threading.Thread = None
running = True


def simulation_loop():
    """Background thread running the physics simulation."""
    global swarm, running

    print("[SimLoop] Starting simulation loop")

    try:
        while running:
            if swarm is not None:
                if not swarm.step():
                    print("[SimLoop] Simulation ended")
                    break
            else:
                asyncio.sleep(0.01)
    except Exception as e:
        print(f"[SimLoop] Error in simulation loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[SimLoop] Simulation loop terminated")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    global swarm, sim_thread, running

    # Startup
    print("[Main] Starting AUS-Lab Swarm Simulation")

    # Initialize swarm
    swarm = SwarmWorld(
        num_drones=args.num,
        gui=not args.headless,
        physics_hz=240,
        control_hz=60
    )

    # Start simulation thread
    running = True
    sim_thread = threading.Thread(target=simulation_loop, daemon=True)
    sim_thread.start()

    print(f"[Main] API server starting on http://localhost:{args.port}")
    print("[Main] Simulation running in background thread")

    yield

    # Shutdown
    print("[Main] Shutting down...")
    running = False

    if sim_thread is not None:
        sim_thread.join(timeout=2.0)

    if swarm is not None:
        swarm.close()

    print("[Main] Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="AUS-Lab Swarm API",
    description="HTTP API for controlling UAV swarm simulation",
    version="1.0.0",
    lifespan=lifespan
)


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AUS-Lab Swarm API",
        "version": "1.0.0",
        "status": "running" if swarm is not None else "not initialized",
        "num_drones": swarm.num_drones if swarm is not None else 0,
        "endpoints": [
            "POST /spawn - Respawn swarm with N drones",
            "POST /takeoff - Take off drones to altitude",
            "POST /land - Land drones",
            "POST /hover - Hover drones at current position",
            "POST /goto - Move single drone to position",
            "POST /velocity - Set drone velocity",
            "POST /formation - Arrange swarm in formation",
            "GET /state - Get all drone states",
            "POST /reset - Reset simulation"
        ]
    }


@app.post("/spawn", response_model=CommandResponse)
async def spawn(request: SpawnRequest):
    """Spawn or respawn swarm with N drones."""
    if swarm is None:
        raise HTTPException(status_code=500, detail="Swarm not initialized")

    cmd = DroneCommand("spawn", "all", {"num": request.num})
    swarm.enqueue_command(cmd)

    return CommandResponse(
        success=True,
        message=f"Respawning with {request.num} drones",
        affected_drones=[]
    )


@app.post("/takeoff", response_model=CommandResponse)
async def takeoff(request: TakeoffRequest):
    """Command drones to take off to specified altitude."""
    if swarm is None:
        raise HTTPException(status_code=500, detail="Swarm not initialized")

    # Resolve drone IDs
    if request.ids == ["all"]:
        drone_ids = "all"
        affected = list(range(swarm.num_drones))
    else:
        drone_ids = request.ids
        affected = request.ids
        # Validate IDs
        for drone_id in drone_ids:
            if drone_id >= swarm.num_drones:
                raise HTTPException(status_code=400, detail=f"Invalid drone ID: {drone_id}")

    cmd = DroneCommand("takeoff", drone_ids, {"altitude": request.altitude})
    swarm.enqueue_command(cmd)

    return CommandResponse(
        success=True,
        message=f"Takeoff commanded to altitude {request.altitude}m",
        affected_drones=affected
    )


@app.post("/land", response_model=CommandResponse)
async def land(request: LandRequest):
    """Command drones to land."""
    if swarm is None:
        raise HTTPException(status_code=500, detail="Swarm not initialized")

    # Resolve drone IDs
    if request.ids == ["all"]:
        drone_ids = "all"
        affected = list(range(swarm.num_drones))
    else:
        drone_ids = request.ids
        affected = request.ids
        # Validate IDs
        for drone_id in drone_ids:
            if drone_id >= swarm.num_drones:
                raise HTTPException(status_code=400, detail=f"Invalid drone ID: {drone_id}")

    cmd = DroneCommand("land", drone_ids, {})
    swarm.enqueue_command(cmd)

    return CommandResponse(
        success=True,
        message="Land commanded",
        affected_drones=affected
    )


@app.post("/hover", response_model=CommandResponse)
async def hover(request: HoverRequest):
    """Command drones to hover at current position."""
    if swarm is None:
        raise HTTPException(status_code=500, detail="Swarm not initialized")

    # Resolve drone IDs
    if request.ids == ["all"]:
        drone_ids = "all"
        affected = list(range(swarm.num_drones))
    else:
        drone_ids = request.ids
        affected = request.ids
        # Validate IDs
        for drone_id in drone_ids:
            if drone_id >= swarm.num_drones:
                raise HTTPException(status_code=400, detail=f"Invalid drone ID: {drone_id}")

    cmd = DroneCommand("hover", drone_ids, {})
    swarm.enqueue_command(cmd)

    return CommandResponse(
        success=True,
        message="Hover commanded",
        affected_drones=affected
    )


@app.post("/goto", response_model=CommandResponse)
async def goto(request: GotoRequest):
    """Command single drone to go to target position."""
    if swarm is None:
        raise HTTPException(status_code=500, detail="Swarm not initialized")

    if request.id >= swarm.num_drones:
        raise HTTPException(status_code=400, detail=f"Invalid drone ID: {request.id}")

    cmd = DroneCommand("goto", [request.id], {
        "id": request.id,
        "x": request.x,
        "y": request.y,
        "z": request.z,
        "yaw": request.yaw
    })
    swarm.enqueue_command(cmd)

    return CommandResponse(
        success=True,
        message=f"Drone {request.id} going to ({request.x}, {request.y}, {request.z})",
        affected_drones=[request.id]
    )


@app.post("/velocity", response_model=CommandResponse)
async def velocity(request: VelocityRequest):
    """Set drone velocity directly."""
    if swarm is None:
        raise HTTPException(status_code=500, detail="Swarm not initialized")

    if request.id >= swarm.num_drones:
        raise HTTPException(status_code=400, detail=f"Invalid drone ID: {request.id}")

    cmd = DroneCommand("velocity", [request.id], {
        "id": request.id,
        "vx": request.vx,
        "vy": request.vy,
        "vz": request.vz,
        "yaw_rate": request.yaw_rate
    })
    swarm.enqueue_command(cmd)

    return CommandResponse(
        success=True,
        message=f"Drone {request.id} velocity set",
        affected_drones=[request.id]
    )


@app.post("/formation", response_model=CommandResponse)
async def formation(request: FormationRequest):
    """Arrange swarm in specified formation."""
    if swarm is None:
        raise HTTPException(status_code=500, detail="Swarm not initialized")

    cmd = DroneCommand("formation", "all", {
        "pattern": request.pattern,
        "center": request.center,
        "spacing": request.spacing,
        "radius": request.radius,
        "axis": request.axis
    })
    swarm.enqueue_command(cmd)

    return CommandResponse(
        success=True,
        message=f"Formation '{request.pattern}' commanded",
        affected_drones=list(range(swarm.num_drones))
    )


@app.get("/state", response_model=StateResponse)
async def state():
    """Get current state of all drones."""
    if swarm is None:
        raise HTTPException(status_code=500, detail="Swarm not initialized")

    state_data = swarm.get_state()
    return StateResponse(**state_data)


@app.post("/reset", response_model=ResetResponse)
async def reset():
    """Reset simulation to initial state."""
    if swarm is None:
        raise HTTPException(status_code=500, detail="Swarm not initialized")

    cmd = DroneCommand("reset", "all", {})
    swarm.enqueue_command(cmd)

    return ResetResponse(
        success=True,
        message="Simulation reset",
        num_drones=swarm.num_drones
    )


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global running
    print("\n[Main] Received interrupt signal, shutting down...")
    running = False
    sys.exit(0)


def main():
    """Main entry point."""
    global args

    # Parse arguments
    parser = argparse.ArgumentParser(description="AUS-Lab UAV Swarm Simulation")
    parser.add_argument("--num", type=int, default=5, help="Number of drones (default: 5)")
    parser.add_argument("--headless", action="store_true", help="Run without GUI")
    parser.add_argument("--port", type=int, default=8000, help="API server port (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="API server host (default: 0.0.0.0)")

    args = parser.parse_args()

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Run server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
