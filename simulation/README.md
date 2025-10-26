# AUS-Lab Swarm Simulation

Minimal Python implementation of a UAV swarm simulation with HTTP API control, built on PyBullet and gym-pybullet-drones.

## Features

- 3D physics-based simulation of N quadrotors (default: 5)
- Real-time control via HTTP REST API
- Multiple formations: line, circle, grid, V-formation
- Position and velocity control modes
- Simple PID controllers for autonomous navigation
- Battery simulation and health monitoring
- GUI and headless modes

## Features Update

- ✅ **GPU Fixed**: Now uses NVIDIA GPU for PyBullet rendering (Ubuntu 24.04 hybrid graphics)
- ✅ **Drones Flying**: Fixed VelocityAviary integration - drones now respond to commands properly
- ✅ **Manual Control**: New keyboard control interface to fly individual drones
- ✅ **Formations Working**: Circle, line, grid, and V-formations fully functional
- ✅ **Real-time API**: All endpoints operational with live drone control

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install gym-pybullet-drones from GitHub (required)
cd ..
git clone https://github.com/utiasDSL/gym-pybullet-drones.git
cd gym-pybullet-drones
pip install -e .
cd ../simulation
```

### Run Simulation

```bash
# Start with GUI (default 5 drones)
python main.py

# Headless mode with 10 drones
python main.py --num 10 --headless

# Custom port
python main.py --port 9000
```

The simulation starts automatically with the API server on `http://localhost:8000`.

### Manual Keyboard Control

Fly a drone manually using keyboard (while simulation runs):

```bash
# Control drone 0 (default)
python manual_control.py

# Control a specific drone (0-4)
python manual_control.py 2
```

**Controls:**
- `W/S` - Forward/Backward
- `A/D` - Left/Right
- `Q/E` - Rotate Left/Right
- `R/F` - Up/Down
- `SPACE` - Hover at current position
- `H` - Return to home (0, 0, 1.5)
- `L` - Land
- `1-5` - Switch between drones
- `ESC` - Exit

You can fly one drone manually while using the API to control the others!

## API Reference

Base URL: `http://localhost:8000`

### GET /

Get API status and available endpoints.

```bash
curl http://localhost:8000/
```

### POST /spawn

Respawn swarm with N drones.

```bash
curl -X POST http://localhost:8000/spawn \
  -H 'Content-Type: application/json' \
  -d '{"num": 8}'
```

### POST /takeoff

Command drones to take off to specified altitude.

```bash
# All drones
curl -X POST http://localhost:8000/takeoff \
  -H 'Content-Type: application/json' \
  -d '{"ids": ["all"], "altitude": 1.0}'

# Specific drones
curl -X POST http://localhost:8000/takeoff \
  -H 'Content-Type: application/json' \
  -d '{"ids": [0, 1, 2], "altitude": 1.5}'
```

### POST /land

Command drones to land.

```bash
# Land all
curl -X POST http://localhost:8000/land \
  -H 'Content-Type: application/json' \
  -d '{"ids": ["all"]}'

# Land specific drones
curl -X POST http://localhost:8000/land \
  -H 'Content-Type: application/json' \
  -d '{"ids": [0, 3]}'
```

### POST /hover

Command drones to hover at current position.

```bash
curl -X POST http://localhost:8000/hover \
  -H 'Content-Type: application/json' \
  -d '{"ids": ["all"]}'
```

### POST /goto

Move a single drone to target position.

```bash
curl -X POST http://localhost:8000/goto \
  -H 'Content-Type: application/json' \
  -d '{"id": 0, "x": 1.0, "y": 0.5, "z": 1.2, "yaw": 0.0}'
```

**Parameters:**
- `id`: Drone ID (integer)
- `x`, `y`: Position in meters (±10.0 bounds)
- `z`: Altitude in meters (0.1 to 5.0)
- `yaw`: Heading in radians (optional, default 0.0)

### POST /velocity

Set drone velocity directly.

```bash
curl -X POST http://localhost:8000/velocity \
  -H 'Content-Type: application/json' \
  -d '{"id": 0, "vx": 0.5, "vy": 0.3, "vz": 0.1, "yaw_rate": 0.0}'
```

**Parameters:**
- `id`: Drone ID
- `vx`, `vy`, `vz`: Velocity components in m/s (±5.0 bounds)
- `yaw_rate`: Yaw rate in rad/s (optional, default 0.0)

### POST /formation

Arrange swarm in specified formation.

```bash
# Circle formation
curl -X POST http://localhost:8000/formation \
  -H 'Content-Type: application/json' \
  -d '{"pattern": "circle", "center": [0, 0, 1.0], "radius": 1.5}'

# Line formation
curl -X POST http://localhost:8000/formation \
  -H 'Content-Type: application/json' \
  -d '{"pattern": "line", "center": [0, 0, 1.0], "spacing": 1.0, "axis": "x"}'

# Grid formation
curl -X POST http://localhost:8000/formation \
  -H 'Content-Type: application/json' \
  -d '{"pattern": "grid", "center": [0, 0, 1.5], "spacing": 0.8}'

# V formation
curl -X POST http://localhost:8000/formation \
  -H 'Content-Type: application/json' \
  -d '{"pattern": "v", "center": [0, 0, 1.0], "spacing": 0.7}'
```

**Patterns:**
- `line`: Linear arrangement along x or y axis
- `circle`: Circular arrangement
- `grid`: Grid arrangement (as square as possible)
- `v`: V-formation (like flying geese)

### GET /state

Get current state of all drones.

```bash
curl http://localhost:8000/state
```

**Response:**
```json
{
  "drones": [
    {
      "id": 0,
      "pos": [0.0, 0.0, 1.0],
      "vel": [0.0, 0.0, 0.0],
      "yaw": 0.0,
      "battery": 98.5,
      "healthy": true
    }
  ],
  "timestamp": 12.5
}
```

### POST /reset

Reset simulation to initial state.

```bash
curl -X POST http://localhost:8000/reset
```

## Python Client Example

```python
import requests
import time

API_BASE = "http://localhost:8000"

# Take off all drones
response = requests.post(f"{API_BASE}/takeoff", json={
    "ids": ["all"],
    "altitude": 1.5
})
print(response.json())

time.sleep(3)

# Circle formation
response = requests.post(f"{API_BASE}/formation", json={
    "pattern": "circle",
    "center": [0, 0, 1.5],
    "radius": 2.0
})
print(response.json())

time.sleep(5)

# Get state
response = requests.get(f"{API_BASE}/state")
state = response.json()
print(f"Drone 0 position: {state['drones'][0]['pos']}")

# Land all
response = requests.post(f"{API_BASE}/land", json={
    "ids": ["all"]
})
print(response.json())
```

## Architecture

```
main.py              - FastAPI server + simulation loop coordinator
swarm.py             - SwarmWorld wrapper around gym-pybullet-drones
controllers.py       - PID controllers and formation planners
api_schemas.py       - Pydantic models for request/response validation
```

**Control Flow:**
1. API receives HTTP request
2. Request validated by Pydantic schemas
3. Command queued to thread-safe queue
4. Simulation loop processes commands
5. PID controllers compute velocity commands
6. gym-pybullet-drones steps physics
7. State observable via `/state` endpoint

## Configuration

### Command-line Arguments

- `--num N`: Number of drones (default: 5, max: 50)
- `--headless`: Run without GUI
- `--port PORT`: API server port (default: 8000)
- `--host HOST`: API server host (default: 0.0.0.0)

### Safety Limits

- Position bounds: ±10.0 m (x, y), 0.1-5.0 m (z)
- Velocity limits: ±2.0 m/s (position control), ±5.0 m/s (velocity control)
- Yaw rate limit: ±π rad/s

## Technical Details

### Physics Simulation

- Engine: PyBullet
- Frequency: 240 Hz physics, 60 Hz control
- Drone model: Crazyflie 2.X quadrotor
- Collisions: Enabled between drones and environment

### Control System

- Position control: 3-axis PID (kp=2.0, ki=0.01, kd=0.5)
- Yaw control: PID (kp=2.0, ki=0.0, kd=0.3)
- Anti-windup: Enabled on all controllers
- Update rate: 60 Hz

### Battery Model

- Initial charge: 100%
- Drain rate: 0.5% per minute (hover)
- Health check: Battery > 0%, within bounds

## Limitations (v1)

- No sensor simulation beyond pose/velocity
- No obstacle avoidance or collision avoidance
- Simplified battery model
- No wind or disturbance simulation
- Single-threaded physics (one background thread)

## Integration with LLM Agents

This API is designed to be controlled by LLM-based agents. High-level natural language commands can be translated to API calls:

**Example LLM → API Translation:**

| Natural Language | API Call |
|------------------|----------|
| "Take off to 2 meters" | `POST /takeoff {"ids":["all"], "altitude":2.0}` |
| "Form a circle" | `POST /formation {"pattern":"circle", "center":[0,0,1.5], "radius":2.0}` |
| "Move drone 0 to (1, 1, 1)" | `POST /goto {"id":0, "x":1.0, "y":1.0, "z":1.0}` |
| "Land the swarm" | `POST /land {"ids":["all"]}` |

See the `agentic/` directory in the parent project for LLM integration examples.

## Troubleshooting

### GUI Issues on Ubuntu 24.04

**"Failed to retrieve a framebuffer config" error:**
- This is fixed automatically in `main.py` for NVIDIA+Intel hybrid systems
- The simulation now uses NVIDIA GPU for rendering
- If you don't have NVIDIA GPU, use `--headless` mode instead

**Detailed troubleshooting:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Common Issues

**Import errors:**
```bash
# Ensure you're in the virtual environment
source .venv/bin/activate
pip install -r requirements.txt
```

**PyBullet GUI not showing:**
- Check you have NVIDIA drivers installed: `nvidia-smi`
- Remove `--headless` flag
- See TROUBLESHOOTING.md for graphics driver issues

**Drones falling immediately:**
- Normal during first few seconds as controllers stabilize
- Use `/takeoff` command to bring drones to stable altitude

**API connection refused:**
- Check server is running: `curl http://localhost:8000/`
- Verify port with `--port` argument
- Check firewall settings

## License

Part of the AUS-Lab project. See parent README for details.
