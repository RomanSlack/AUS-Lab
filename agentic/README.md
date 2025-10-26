# Agentic Swarm Controller

LLM-powered natural language control for UAV swarms.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file in parent directory with:
GEMINI_API_KEY=your_key_here

# Start simulation (in another terminal)
cd ../simulation && python main.py

# Run controller
python main.py -c "Take off to 2 meters and form a circle"

# Interactive mode
python main.py
```

## Usage

```bash
# Single command
python main.py -c "Land all drones"

# Dry run (plan only)
python main.py -c "Survey the area" --dry-run

# Custom API endpoint
python main.py --api http://192.168.1.100:8000 -c "Takeoff"
```