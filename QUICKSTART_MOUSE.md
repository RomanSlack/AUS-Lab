# Mouse Interaction - Quick Start

## 30-Second Guide

1. **Start simulation:**
   ```bash
   cd simulation && python main.py
   ```

2. **Click in PyBullet window**

3. **Copy coordinates from console:**
   ```
   [Mouse Click] Copy this for agentic system: 2.50, 3.10, 0.00
   ```

4. **Use in agentic command:**
   ```bash
   cd ../agentic && python main.py -c "Fly to coordinates 2.50, 3.10, 1.50"
   ```

Done! 🎯

## Visual Guide

```
┌─────────────────────────────┐
│   PyBullet 3D Viewport      │
│                             │
│         🖱️ CLICK HERE        │
│            ↓                │
│         ❌ (marker)         │
│                             │
│   Drones: ✈️ ✈️ ✈️          │
└─────────────────────────────┘

Console Output:
[Mouse Click] Coordinates: (2.50, 3.10, 0.00)
[Mouse Click] Copy this for agentic system: 2.50, 3.10, 0.00

Then use:
"Fly to coordinates 2.50, 3.10, 1.50"
```

## Common Commands

| Command | What It Does |
|---------|--------------|
| `"Fly to coordinates X, Y, Z"` | Swarm flies to clicked point |
| `"Intercept position X, Y, Z"` | Same as above |
| `"Form circle at X, Y, Z"` | Circle formation at location |
| `"Send drone 0 to X, Y, Z"` | Individual drone movement |

## API Alternative

```bash
# After clicking in GUI:
curl http://localhost:8000/click

# Returns:
{
  "has_click": true,
  "coords": [2.50, 3.10, 0.00],
  "message": "Last click at (2.50, 3.10, 0.00)"
}
```

## Troubleshooting

**No coordinates appearing?**
→ Make sure you clicked inside the 3D viewport area

**Running headless?**
→ Mouse only works with GUI: remove `--headless` flag

**Need more help?**
→ See `MOUSE_INTERACTION_GUIDE.md` for full documentation
