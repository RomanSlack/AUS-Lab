# AUS-Lab

Research platform investigating the connection between Swarm Structures, Hardware-in-the-Loop (HIL), Agentic Systems, and Large Language Models.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Rust](https://img.shields.io/badge/Rust-1.75-000000?logo=rust&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=react&logoColor=black)
![Three.js](https://img.shields.io/badge/Three.js-0.159-000000?logo=threedotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?logo=typescript&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Gemini-API-4285F4?logo=google&logoColor=white)

## Overview

AUS-Lab provides a complete ecosystem for UAV swarm simulation with LLM-driven autonomous control. The platform features a high-performance Rust physics engine, a React/Three.js web visualization frontend, and an agentic system that translates natural language commands into structured drone operations.

## Architecture

```
User (CLI / Web UI)
        |
        v
  Agentic Controller  -->  Google Gemini API
        |
        v
   FastAPI Server (REST + WebSocket)
        |
        v
  Rust Physics Engine
        |
        v
  Three.js Web Frontend (real-time visualization)
```

## Project Structure

```
AUS-Lab/
├── agentic/           # LLM-driven swarm controller
├── simulation/        # Rust physics engine + FastAPI server
│   └── rust_physics/  # Rust source code (PyO3 bindings)
└── web_simulation/    # React + Three.js frontend
```

## Prerequisites

- Python 3.12+
- Rust 1.75+ (with cargo)
- Node.js 18+
- Google Gemini API key

## Setup

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

### 2. Build Rust Physics Engine

```bash
cd simulation/rust_physics
cargo build --release
pip install maturin
maturin develop --release
```

### 3. Install Python Dependencies

```bash
# Simulation server
cd simulation
pip install -r requirements.txt

# Agentic controller
cd ../agentic
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies

```bash
cd web_simulation
npm install
```

## Running the Platform

### Terminal 1: Start Simulation Server

```bash
cd simulation
python main.py --num 24 --web
```

Options:
- `--num N` - Number of drones (default: 24)
- `--web` - Use Rust physics engine with WebSocket streaming (recommended)
- `--port PORT` - API port (default: 8000)

### Terminal 2: Start Web Frontend

```bash
cd web_simulation
npm run dev
```

Access the visualization at `http://localhost:5173`

### Terminal 3: Run Agentic Controller

Interactive mode:
```bash
cd agentic
python main.py
```

Single command:
```bash
python main.py -c "Take off to 2 meters and form a circle"
```

Dry run (plan only):
```bash
python main.py -c "Survey the area" --dry-run
```

## API Endpoints

The simulation server exposes REST endpoints at `http://localhost:8000`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/state` | GET | Current swarm state |
| `/takeoff` | POST | Take off to altitude |
| `/land` | POST | Land drones |
| `/goto` | POST | Move drone to position |
| `/formation` | POST | Arrange swarm pattern |
| `/hivemind/enable` | POST | Enable hivemind mode |
| `/hivemind/move` | POST | Move swarm as unit |

WebSocket endpoint: `ws://localhost:8000/ws` (real-time state updates)

## Supported Actions

The agentic controller supports these action types:

- `takeoff` - Take off to specified altitude (0.1-5.0m)
- `land` - Land at current position
- `hover` - Hold position
- `goto` - Move single drone to coordinates
- `velocity` - Set drone velocity directly
- `formation` - Arrange swarm (circle, line, grid, v-formation)
- `enable_hivemind` / `disable_hivemind` - Toggle hivemind mode
- `move_hivemind` - Move entire swarm as single entity

## Example Commands

```
"Take off all drones to 1.5 meters"
"Form a circle at altitude 2 meters with radius 3 meters"
"Send drone 0 to position 3, 2, 1.5"
"Enable hivemind and move the swarm to 5, 5, 2"
"Land all drones"
```

## License

MIT
