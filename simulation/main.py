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
import time
from contextlib import asynccontextmanager

# Fix for hybrid Intel/NVIDIA systems: Force NVIDIA GPU for PyBullet GUI
# This resolves "Failed to retrieve a framebuffer config" errors on Ubuntu 24.04
# Must be set BEFORE importing pybullet
os.environ['__NV_PRIME_RENDER_OFFLOAD'] = '1'
os.environ['__GLX_VENDOR_LIBRARY_NAME'] = 'nvidia'

# Try to reduce flickering with these NVIDIA settings
os.environ['__GL_SYNC_TO_VBLANK'] = '0'
os.environ['vblank_mode'] = '0'

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json

from swarm import SwarmWorld, DroneCommand
from api_schemas import (
    SpawnRequest, TakeoffRequest, LandRequest, HoverRequest,
    GotoRequest, VelocityRequest, FormationRequest,
    StateResponse, CommandResponse, ResetResponse, ClickCoordsResponse
)


# Global swarm instance
swarm: SwarmWorld = None
sim_thread: threading.Thread = None
running = True
web_mode = False  # WebSocket mode flag


class ConnectionManager:
    """Manages WebSocket connections for real-time state broadcasting."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WebSocket] Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WebSocket] Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


def run_api_server():
    """Background thread running the API server."""
    print("[APIServer] Starting FastAPI server")
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )

def simulation_loop():
    """Main thread running the physics simulation with GUI."""
    global swarm, running

    print("[SimLoop] Starting simulation loop in MAIN THREAD", flush=True)

    try:
        step_count = 0
        while running:
            if swarm is not None:
                if step_count == 0:
                    print(f"[SimLoop] Beginning first step...", flush=True)
                if not swarm.step():
                    print("[SimLoop] Simulation ended", flush=True)
                    break
                step_count += 1
                if step_count % 240 == 0:  # Print every second
                    print(f"[SimLoop] Running... {step_count} steps completed", flush=True)
            else:
                time.sleep(0.01)
    except Exception as e:
        print(f"[SimLoop] Error in simulation loop: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        print("[SimLoop] Simulation loop terminated", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Just a placeholder now since we manage lifecycle in main()
    yield


# Create FastAPI app with enhanced documentation
app = FastAPI(
    title="AUS-Lab Swarm API",
    description="""
## Autonomous UAV Swarm Control API

Control a physics-based multi-drone simulation with real-time commands.

### Features
* **Real-time Control**: Command individual drones or entire swarm
* **Formations**: Circle, line, grid, and V-formation patterns
* **Physics Simulation**: 240Hz physics, 60Hz control loop
* **State Monitoring**: Query real-time position, velocity, battery, health

### Quick Start
1. Start simulation: `python main.py`
2. Open this page: http://localhost:8000/docs
3. Try the "Takeoff" endpoint to see drones fly!
4. Use "Formation" to arrange drones in patterns

### External Control
- **Manual Control**: `python manual_control.py` for keyboard control
- **Python Client**: See README.md for examples
- **LLM Integration**: Natural language → API translation layer (coming soon)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Endpoints

@app.get("/", tags=["Status"])
async def root():
    """
    **API Status and Information**

    Returns current status of the simulation and available endpoints.
    Use this to check if the simulation is running properly.
    """
    return {
        "name": "AUS-Lab Swarm API",
        "version": "1.0.0",
        "status": "running" if swarm is not None else "not initialized",
        "num_drones": swarm.num_drones if swarm is not None else 0,
        "docs": "http://localhost:8000/docs",
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


@app.post("/spawn", response_model=CommandResponse, tags=["Swarm Management"])
async def spawn(request: SpawnRequest):
    """
    **Respawn Swarm with N Drones**

    Resets the simulation and spawns a new swarm with the specified number of drones.
    All drones start on the ground in a grid formation.

    - **num**: Number of drones (1-50)
    """
    if swarm is None:
        raise HTTPException(status_code=500, detail="Swarm not initialized")

    cmd = DroneCommand("spawn", "all", {"num": request.num})
    swarm.enqueue_command(cmd)

    return CommandResponse(
        success=True,
        message=f"Respawning with {request.num} drones",
        affected_drones=[]
    )


@app.post("/takeoff", response_model=CommandResponse, tags=["Basic Flight"])
async def takeoff(request: TakeoffRequest):
    """
    **Takeoff to Altitude**

    Commands drones to take off from ground to the specified altitude.

    - **ids**: List of drone IDs or ["all"] for all drones
    - **altitude**: Target altitude in meters (0.1 to 5.0)

    **Example:** Take all drones to 1.5 meters
    ```json
    {"ids": ["all"], "altitude": 1.5}
    ```
    """
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


@app.post("/land", response_model=CommandResponse, tags=["Basic Flight"])
async def land(request: LandRequest):
    """
    **Land Drones**

    Commands drones to descend and land on the ground.

    - **ids**: List of drone IDs or ["all"] for all drones
    """
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


@app.post("/hover", response_model=CommandResponse, tags=["Basic Flight"])
async def hover(request: HoverRequest):
    """
    **Hover at Current Position**

    Commands drones to maintain their current position and altitude.

    - **ids**: List of drone IDs or ["all"] for all drones
    """
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


@app.post("/goto", response_model=CommandResponse, tags=["Advanced Control"])
async def goto(request: GotoRequest):
    """
    **Move Drone to Position**

    Commands a single drone to fly to the specified 3D position.

    - **id**: Drone ID (0-indexed)
    - **x, y**: Position in meters (±10.0 bounds)
    - **z**: Altitude in meters (0.1 to 5.0)
    - **yaw**: Heading in radians (optional, default 0.0)

    **Example:** Move drone 0 to (2, 1, 1.5)
    ```json
    {"id": 0, "x": 2.0, "y": 1.0, "z": 1.5, "yaw": 0.0}
    ```
    """
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


@app.post("/velocity", response_model=CommandResponse, tags=["Advanced Control"])
async def velocity(request: VelocityRequest):
    """
    **Set Drone Velocity**

    Directly sets the velocity of a single drone (advanced control).

    - **id**: Drone ID
    - **vx, vy, vz**: Velocity components in m/s (±5.0 bounds)
    - **yaw_rate**: Yaw rate in rad/s (optional, default 0.0)

    **Example:** Move drone 0 forward at 1 m/s
    ```json
    {"id": 0, "vx": 1.0, "vy": 0.0, "vz": 0.0, "yaw_rate": 0.0}
    ```
    """
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


@app.post("/formation", response_model=CommandResponse, tags=["Swarm Formations"])
async def formation(request: FormationRequest):
    """
    **Arrange Swarm in Formation**

    Commands the entire swarm to arrange into a specified geometric formation.

    - **pattern**: Formation type ("circle", "line", "grid", "v")
    - **center**: Formation center point [x, y, z]
    - **spacing**: Distance between drones (0.5-3.0m, for line/grid/v)
    - **radius**: Circle radius (0.5-5.0m, for circle only)
    - **axis**: Line direction ("x" or "y", for line only)

    **Examples:**

    Circle formation:
    ```json
    {"pattern": "circle", "center": [0, 0, 2.0], "radius": 2.0}
    ```

    Line formation:
    ```json
    {"pattern": "line", "center": [0, 0, 1.5], "spacing": 1.0, "axis": "x"}
    ```

    Grid formation:
    ```json
    {"pattern": "grid", "center": [0, 0, 1.5], "spacing": 0.8}
    ```

    V formation (like flying geese):
    ```json
    {"pattern": "v", "center": [0, 0, 1.5], "spacing": 0.7}
    ```
    """
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


@app.get("/state", response_model=StateResponse, tags=["Status"])
async def state():
    """
    **Get Drone States**

    Returns the current state of all drones in the simulation.

    **Response includes for each drone:**
    - **id**: Drone identifier (0-indexed)
    - **pos**: Position [x, y, z] in meters
    - **vel**: Velocity [vx, vy, vz] in m/s
    - **yaw**: Heading angle in radians
    - **battery**: Battery percentage (0-100%)
    - **healthy**: Health status (true if drone is operational)

    **Plus:**
    - **timestamp**: Simulation time in seconds
    """
    if swarm is None:
        raise HTTPException(status_code=500, detail="Swarm not initialized")

    state_data = swarm.get_state()
    return StateResponse(**state_data)


@app.post("/reset", response_model=ResetResponse, tags=["Swarm Management"])
async def reset():
    """
    **Reset Simulation**

    Resets the entire simulation to its initial state.

    All drones return to starting positions on the ground.
    Simulation time, batteries, and controllers are reset.
    """
    if swarm is None:
        raise HTTPException(status_code=500, detail="Swarm not initialized")

    cmd = DroneCommand("reset", "all", {})
    swarm.enqueue_command(cmd)

    return ResetResponse(
        success=True,
        message="Simulation reset",
        num_drones=swarm.num_drones
    )


@app.get("/click", response_model=ClickCoordsResponse, tags=["Mouse Interaction"])
async def get_click_coords():
    """
    **Get Last Clicked Coordinates**

    Returns the coordinates of the last mouse click in the PyBullet GUI.

    **Use Case:**
    1. Click in the 3D GUI viewport
    2. Call this endpoint to retrieve the clicked coordinates
    3. Use coordinates in agentic commands or direct API calls

    **Response:**
    - **has_click**: Whether any click has been registered
    - **coords**: [x, y, z] world coordinates of the click
    - **message**: Human-readable status message

    **Note:** Only works when GUI is enabled (not in headless mode)
    """
    if swarm is None:
        raise HTTPException(status_code=500, detail="Swarm not initialized")

    if swarm.last_clicked_coords is None:
        return ClickCoordsResponse(
            has_click=False,
            coords=[],
            message="No click registered yet. Click in the GUI viewport to set coordinates."
        )

    x, y, z = swarm.last_clicked_coords
    return ClickCoordsResponse(
        has_click=True,
        coords=[x, y, z],
        message=f"Last click at ({x:.2f}, {y:.2f}, {z:.2f})"
    )


# WebSocket endpoint for real-time communication

def handle_websocket_command(payload: dict) -> dict:
    """Handle a command received via WebSocket."""
    if swarm is None:
        return {"success": False, "message": "Swarm not initialized"}

    action = payload.get("action")
    params = payload.get("params", {})

    try:
        if action == "takeoff":
            ids = params.get("ids", ["all"])
            altitude = params.get("altitude", 1.0)
            drone_ids = "all" if ids == ["all"] else ids
            cmd = DroneCommand("takeoff", drone_ids, {"altitude": altitude})
            swarm.enqueue_command(cmd)
            return {"success": True, "message": f"Takeoff to {altitude}m"}

        elif action == "land":
            ids = params.get("ids", ["all"])
            drone_ids = "all" if ids == ["all"] else ids
            cmd = DroneCommand("land", drone_ids, {})
            swarm.enqueue_command(cmd)
            return {"success": True, "message": "Land commanded"}

        elif action == "hover":
            ids = params.get("ids", ["all"])
            drone_ids = "all" if ids == ["all"] else ids
            cmd = DroneCommand("hover", drone_ids, {})
            swarm.enqueue_command(cmd)
            return {"success": True, "message": "Hover commanded"}

        elif action == "goto":
            cmd = DroneCommand("goto", [params["id"]], params)
            swarm.enqueue_command(cmd)
            return {"success": True, "message": f"Drone {params['id']} going to position"}

        elif action == "velocity":
            cmd = DroneCommand("velocity", [params["id"]], params)
            swarm.enqueue_command(cmd)
            return {"success": True, "message": f"Drone {params['id']} velocity set"}

        elif action == "formation":
            cmd = DroneCommand("formation", "all", params)
            swarm.enqueue_command(cmd)
            return {"success": True, "message": f"Formation '{params.get('pattern')}' commanded"}

        elif action == "spawn":
            num = params.get("num", 5)
            cmd = DroneCommand("spawn", "all", {"num": num})
            swarm.enqueue_command(cmd)
            return {"success": True, "message": f"Spawning {num} drones"}

        elif action == "reset":
            cmd = DroneCommand("reset", "all", {})
            swarm.enqueue_command(cmd)
            return {"success": True, "message": "Simulation reset"}

        else:
            return {"success": False, "message": f"Unknown action: {action}"}

    except Exception as e:
        return {"success": False, "message": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time bidirectional communication.

    Sends state updates at 60Hz and receives commands.
    """
    await manager.connect(websocket)

    async def send_state():
        """Send state updates to this client at 60Hz."""
        try:
            while True:
                if swarm is not None:
                    state_data = swarm.get_state()
                    await websocket.send_json({
                        "type": "state",
                        "payload": {
                            "drones": state_data["drones"],
                            "timestamp": state_data["timestamp"]
                        }
                    })
                await asyncio.sleep(1/60)  # 60Hz
        except Exception as e:
            print(f"[WebSocket] Send error: {e}")

    async def receive_commands():
        """Receive and handle commands from this client."""
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get("type") == "command":
                    result = handle_websocket_command(message.get("payload", {}))
                    await websocket.send_json({
                        "type": "ack",
                        "payload": result
                    })
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"[WebSocket] Receive error: {e}")

    # Run both tasks concurrently
    send_task = asyncio.create_task(send_state())
    receive_task = asyncio.create_task(receive_commands())

    try:
        # Wait for either task to complete (usually due to disconnect)
        done, pending = await asyncio.wait(
            [send_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        # Cancel the other task
        for task in pending:
            task.cancel()
    finally:
        manager.disconnect(websocket)


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global running
    print("\n[Main] Received interrupt signal, shutting down...")
    running = False
    sys.exit(0)


def main():
    """Main entry point."""
    global args, swarm, sim_thread, running, web_mode

    # Parse arguments
    parser = argparse.ArgumentParser(description="AUS-Lab UAV Swarm Simulation")
    parser.add_argument("--num", type=int, default=5, help="Number of drones (default: 5)")
    parser.add_argument("--headless", action="store_true", help="Run without GUI")
    parser.add_argument("--legacy-gui", action="store_true",
                        help="Use legacy PyBullet GUI instead of custom renderer (may flicker on some systems)")
    parser.add_argument("--web", action="store_true",
                        help="Enable web mode: runs headless with WebSocket streaming for Three.js frontend")
    parser.add_argument("--port", type=int, default=8000, help="API server port (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="API server host (default: 0.0.0.0)")

    args = parser.parse_args()

    # Web mode implies headless
    web_mode = args.web
    if web_mode:
        args.headless = True

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)

    print("[Main] Starting AUS-Lab Swarm Simulation")

    # Determine which renderer to use
    use_custom = not args.legacy_gui

    # Initialize swarm in main thread
    swarm = SwarmWorld(
        num_drones=args.num,
        gui=not args.headless,
        physics_hz=240,
        control_hz=60,
        use_custom_renderer=use_custom
    )

    # Start API server in background thread
    running = True
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()

    print(f"[Main] API server starting on http://{args.host}:{args.port}")
    print(f"\n{'='*60}")
    if web_mode:
        print(f"  WEB MODE ENABLED - Headless with WebSocket streaming")
        print(f"  WebSocket URL:        ws://localhost:{args.port}/ws")
        print(f"  Start web frontend:   cd web_simulation && npm run dev")
    else:
        print(f"  Interactive API Docs: http://localhost:{args.port}/docs")
        print(f"  Alternative Docs:     http://localhost:{args.port}/redoc")
        print(f"  Manual Control:       python manual_control.py")
    print(f"{'='*60}\n")

    # Give API server time to start
    time.sleep(1)

    # Run simulation loop in main thread (required for PyBullet mouse events)
    try:
        simulation_loop()
    except KeyboardInterrupt:
        print("\n[Main] Keyboard interrupt received")
    finally:
        print("[Main] Shutting down...")
        running = False
        if swarm is not None:
            swarm.close()
        print("[Main] Cleanup complete")


if __name__ == "__main__":
    main()
