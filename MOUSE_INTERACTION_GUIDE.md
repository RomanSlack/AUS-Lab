# Mouse Interaction Guide

## Overview

AUS-Lab now supports **interactive mouse click** functionality in the PyBullet GUI. Click anywhere in the 3D viewport to capture world coordinates, which can then be used to command the drone swarm.

## Features

- **Click-to-coordinate**: Left-click in GUI to get 3D world coordinates
- **Visual feedback**: Red cross marker and text label appear at clicked location
- **Console output**: Coordinates printed to simulation terminal
- **API access**: Retrieve coordinates via HTTP endpoint
- **Agentic integration**: Use coordinates in natural language commands

## How It Works

### 1. Visual Workflow

```
User clicks in PyBullet GUI
    ↓
Mouse handler captures screen position
    ↓
Ray casting converts to 3D world coordinates
    ↓
Visual marker appears at clicked location
    ↓
Coordinates printed to console
    ↓
User copies coordinates
    ↓
Paste into agentic system command
    ↓
Swarm flies to clicked point
```

### 2. Technical Implementation

**Components:**
- `mouse_handler.py` - Mouse event processing and coordinate conversion
- `swarm.py` - Integration into simulation loop
- `main.py` - API endpoint for coordinate retrieval
- `translation_schema.py` - LLM instruction updates

**Key Functions:**
- `MouseInteractionHandler.process_mouse_events()` - Poll mouse clicks
- `MouseInteractionHandler._screen_to_world()` - Convert 2D → 3D coordinates
- `MouseInteractionHandler._update_visual_feedback()` - Draw markers

## Usage

### Method 1: Manual Copy-Paste (Simplest)

**Step 1:** Start the simulation with GUI enabled
```bash
cd /home/roman/AUS-Lab/simulation
source .venv/bin/activate
python main.py
```

**Step 2:** Click anywhere in the PyBullet window

**Step 3:** Check the simulation terminal for output:
```
[Mouse Click] Coordinates: (2.50, 3.10, 0.00)
[Mouse Click] Copy this for agentic system: 2.50, 3.10, 0.00
```

**Step 4:** In agentic terminal, use the coordinates:
```bash
cd /home/roman/AUS-Lab/agentic
source .venv/bin/activate
python main.py -c "Fly to coordinates 2.50, 3.10, 1.50"
```

### Method 2: API Retrieval

**Step 1:** Click in the GUI (as above)

**Step 2:** Query the API endpoint:
```bash
curl http://localhost:8000/click
```

**Response:**
```json
{
  "has_click": true,
  "coords": [2.50, 3.10, 0.00],
  "message": "Last click at (2.50, 3.10, 0.00)"
}
```

**Step 3:** Use coordinates in your application or agentic system

### Method 3: Interactive API Documentation

**Step 1:** Open browser to `http://localhost:8000/docs`

**Step 2:** Navigate to **Mouse Interaction** → `GET /click`

**Step 3:** Click "Try it out" → "Execute"

**Step 4:** View coordinates in response body

## Visual Feedback

When you click in the GUI, you'll see:

**1. Cross Marker:**
- Two perpendicular red lines on ground plane
- Marks exact X,Y position

**2. Vertical Line:**
- Red line extending 0.5m upward from ground
- Makes marker visible from different camera angles

**3. Text Label:**
- White text showing coordinates
- Positioned 0.6m above ground
- Format: `Click: (x.xx, y.xx, z.xx)`

**4. Auto-removal:**
- Visual feedback disappears after 5 seconds
- Or when a new click is made

## Coordinate System

**Ground Plane:** Z = 0.0 meters

**Bounds:**
- X: -10.0 to +10.0 meters
- Y: -10.0 to +10.0 meters
- Z: 0.0 (ground) to 5.0 meters (max altitude)

**Camera View:**
- Default distance: 3 meters
- Yaw: -30°
- Pitch: -30°
- Target: Origin (0, 0, 0)

## Agentic System Commands

The LLM has been trained to understand coordinate-based commands:

### Example Commands

**Direct coordinates:**
```
"Fly to coordinates 2.5, 3.1, 1.5"
```

**Intercept language:**
```
"Intercept position 2.5, 3.1, 1.5"
```

**With altitude:**
```
"Move swarm to 2.5, 3.1 at altitude 2.0"
```

**Formation at coordinates:**
```
"Form a circle at position 2.5, 3.1, 1.5 with radius 2 meters"
```

**Individual drone:**
```
"Send drone 0 to position 2.5, 3.1, 1.5"
```

### How the LLM Interprets Coordinates

The system prompt includes rules for parsing coordinates:

**Rule 11:** "When user provides explicit coordinates (e.g., 'fly to 2.5, 3.1, 1.5'), parse them as x, y, z"

**Rule 12:** "Coordinates can come from GUI clicks - treat them as target waypoints"

**Rule 13:** "For 'intercept' or 'fly to' commands with coordinates, use formation with center at those coords"

**Example transformation:**
```
User: "Fly to coordinates 2.5, 3.1, 1.5"
    ↓
LLM generates:
{
  "mission_name": "Fly to clicked position",
  "actions": [
    {
      "action_type": "takeoff",
      "drone_ids": "all",
      "parameters": {"altitude": 1.5}
    },
    {
      "action_type": "formation",
      "drone_ids": "all",
      "parameters": {
        "pattern": "circle",
        "center": [2.5, 3.1, 1.5],
        "radius": 1.0
      }
    }
  ]
}
```

## API Reference

### GET /click

**Description:** Retrieve last clicked coordinates

**Response:** `ClickCoordsResponse`
```json
{
  "has_click": boolean,
  "coords": [x, y, z],
  "message": string
}
```

**Status Codes:**
- 200: Success
- 500: Swarm not initialized

**Example:**
```bash
curl http://localhost:8000/click
```

## Troubleshooting

### "No mouse events detected"
**Cause:** Running in headless mode
**Solution:** Start simulation without `--headless` flag

### "Clicks not registering"
**Cause:** PyBullet window not in focus
**Solution:** Click directly on the 3D viewport area, not the window border

### "Coordinates seem wrong"
**Cause:** Clicking on drones or air instead of ground
**Solution:** System uses ground plane (Z=0) intersection. Coordinates are correct for ground point below cursor.

### "Visual marker not appearing"
**Cause:** Marker lifespan expired (5 seconds)
**Solution:** Click again to create new marker

### "Agentic system not understanding coordinates"
**Cause:** Incorrect format or out of bounds
**Solution:** Use format "x, y, z" with values within ±10m (x,y) and 0-5m (z)

## Advanced Usage

### Programmatic Mouse Click Handling

If you want to integrate mouse clicks into your own code:

```python
from mouse_handler import MouseInteractionHandler

# Initialize handler
physics_client_id = swarm.env.getPyBulletClient()
mouse_handler = MouseInteractionHandler(
    physics_client_id=physics_client_id,
    ground_height=0.0
)

# In your simulation loop
while running:
    coords = mouse_handler.process_mouse_events()
    if coords is not None:
        x, y, z = coords
        print(f"Clicked at: {x}, {y}, {z}")
        # Use coordinates for your application
```

### Custom Visual Feedback

Modify marker appearance in `mouse_handler.py`:

```python
# Change marker color (RGB)
self.marker_color = [1, 0, 0]  # Red (default)
self.marker_color = [0, 1, 0]  # Green
self.marker_color = [0, 0, 1]  # Blue

# Change marker size
self.marker_size = 0.1  # Default

# Change marker duration
self.marker_duration = 5.0  # seconds
```

### Multiple Click Storage

Currently, only the last click is stored. To store multiple waypoints:

**Modify `swarm.py`:**
```python
# Replace
self.last_clicked_coords: Optional[Tuple[float, float, float]] = None

# With
self.clicked_waypoints: List[Tuple[float, float, float]] = []
```

Then update the click handler to append instead of replace.

## Limitations

1. **Ground Plane Only:** Clicks are projected onto Z=0 ground plane
2. **No Object Selection:** Cannot select individual drones by clicking
3. **GUI Mode Only:** Requires GUI enabled (not available in headless)
4. **Thread Safety:** All mouse operations must run in simulation thread
5. **Single Click Storage:** Only last click is remembered (by default)

## Future Enhancements

Potential improvements for future versions:

- [ ] Click and drag for area selection
- [ ] Click on drones to select individual UAVs
- [ ] Multi-waypoint path planning from multiple clicks
- [ ] Right-click menu for quick commands
- [ ] Height adjustment via scroll wheel
- [ ] Visual path preview before execution
- [ ] Click-to-target enemy/objective markers

## Technical Details

### Screen-to-World Coordinate Math

The conversion uses ray casting:

1. **Get camera matrices** - View and projection from PyBullet
2. **Normalize screen coords** - Map pixels to [-1, 1] clip space
3. **Create ray in clip space** - [norm_x, norm_y, -1, 1]
4. **Transform to eye space** - Apply inverse projection matrix
5. **Transform to world space** - Apply inverse view matrix
6. **Calculate intersection** - Solve ray-plane intersection for Z=0

### Ray-Plane Intersection Formula

```
Ray: P = camera_pos + t * ray_direction
Plane: Z = 0

Solve for t:
camera_pos.z + t * ray_direction.z = 0
t = -camera_pos.z / ray_direction.z

Intersection: P = camera_pos + t * ray_direction
```

## Files Modified/Created

| File | Status | Purpose |
|------|--------|---------|
| `simulation/mouse_handler.py` | **NEW** | Mouse event handling and coordinate conversion |
| `simulation/swarm.py` | Modified | Integration of mouse handler into simulation loop |
| `simulation/main.py` | Modified | Added `/click` API endpoint |
| `simulation/api_schemas.py` | Modified | Added `ClickCoordsResponse` schema |
| `agentic/translation_schema.py` | Modified | Updated LLM system prompt with coordinate rules |

## Summary

Mouse interaction provides an intuitive way to command drone swarms by clicking target locations in the 3D environment. The system seamlessly integrates with both the API and agentic control layers, allowing for flexible workflow options from manual copy-paste to fully automated execution.

**Quick Start:**
1. Start simulation with GUI
2. Click in viewport
3. Copy coordinates from console
4. Use in agentic command: `"Fly to coordinates X, Y, Z"`

For questions or issues, see the main README or open a GitHub issue.
