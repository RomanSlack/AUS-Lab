# Mouse Interaction Workaround

## Issue

PyBullet's `getMouseEvents()` and `getKeyboardEvents()` don't work reliably when:
1. Running in a background thread (our simulation loop)
2. Camera manipulation is enabled (drag to rotate/pan)
3. The GUI window isn't the primary focus

This is a known PyBullet limitation.

## Workaround Solutions

### Option 1: Manual Coordinate Entry (Simplest)

Just estimate or type coordinates directly:

```bash
# Terminal 1: Run simulation
cd /home/roman/AUS-Lab/simulation
python main.py

# Terminal 2: Use agentic system with coordinates
cd /home/roman/AUS-Lab/agentic
python main.py -c "Fly to coordinates 2.0, 3.0, 1.5"
```

**Tips for estimating coordinates:**
- Origin (0, 0) is at the center where drones spawn
- Each drone is about 0.5m apart initially
- Ground plane is Z=0
- Bounds: X/Y within ±10m, Z between 0.1-5.0m

### Option 2: Click Capture Tool

Use the terminal-based coordinate entry tool:

```bash
# Terminal 1: Run simulation
cd /home/roman/AUS-Lab/simulation
python main.py

# Terminal 2: Run click capture tool
cd /home/roman/AUS-Lab/simulation
python click_capture.py
```

Then:
1. Press **SPACE**
2. Enter X, Y, Z coordinates when prompted
3. Copy the generated command
4. Use in agentic system

### Option 3: Use Drone Positions

Click on a drone in the GUI and see its position in your simulation view, then use those coordinates:

```bash
# Get all drone positions via API
curl http://localhost:8000/state | jq '.drones[] | {id, pos}'

# Use a drone's position as target
python main.py -c "Form circle at position 2.5, 1.3, 1.5"
```

### Option 4: Interactive Grid System (Future)

We could add a visual grid overlay with numbered waypoints that can be selected via keyboard (1-9 keys).

## Why Mouse Events Don't Work

**Technical Explanation:**

PyBullet's event system has limitations:
- `getMouseEvents()` returns empty when camera manipulation is active
- Events are only captured when GUI window has exclusive focus
- Background threads don't receive GUI events reliably
- The simulation runs at 240Hz in a separate thread from the GUI

**Attempted Solutions:**
- ✓ Enabled `COV_ENABLE_MOUSE_PICKING`
- ✓ Tried keyboard events as fallback ('C' key)
- ✓ Added extensive debug logging
- ✗ Events still not captured

**Root Cause:**
The PyBullet GUI runs in the main thread, but our simulation loop runs in a background thread. PyBullet doesn't provide a proper event callback system, only polling - which doesn't work across threads.

## Recommended Approach

**For now:** Use **Option 1** (manual coordinate entry) or **Option 2** (click capture tool).

The agentic system already understands coordinate-based commands perfectly:
- "Fly to coordinates X, Y, Z"
- "Intercept position X, Y, Z"
- "Form circle at X, Y, Z"

## Future Solutions

To properly fix this would require:

1. **Web-based 3D viewer** - Use Three.js/Babylon.js with proper JavaScript mouse events
2. **Separate GUI process** - Run PyBullet GUI in main thread, simulation in subprocess
3. **Custom PyBullet build** - Modify PyBullet source to add proper event callbacks
4. **Alternative renderer** - Use MuJoCo, Isaac Sim, or Unity which have better event systems

For this project's scope, manual coordinate entry is the most practical solution.
