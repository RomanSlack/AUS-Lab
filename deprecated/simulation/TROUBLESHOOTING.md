# Troubleshooting Guide

## PyBullet GUI "Failed to retrieve a framebuffer config" Error

### Problem
On Ubuntu 24.04 with hybrid Intel Arc + NVIDIA graphics, PyBullet GUI fails with:
```
Failed to retrieve a framebuffer config
```

### Root Cause
PyBullet's OpenGL context creation fails when using Intel Arc graphics for GLX/X11 rendering. The Intel driver doesn't provide the framebuffer configuration that PyBullet expects.

### Solution
Force PyBullet to use the NVIDIA GPU instead of Intel Arc by setting environment variables **before** importing pybullet.

The fix is already implemented in `main.py`:
```python
import os
os.environ['__NV_PRIME_RENDER_OFFLOAD'] = '1'
os.environ['__GLX_VENDOR_LIBRARY_NAME'] = 'nvidia'
```

### Verification
When running successfully, you should see in the output:
```
GL_VENDOR=NVIDIA Corporation
GL_RENDERER=NVIDIA GeForce RTX 4060 Laptop GPU/PCIe/SSE2
GL_VERSION=3.3.0 NVIDIA 580.95.05
```

## Gymnasium API Compatibility

### Problem
```
ValueError: too many values to unpack (expected 4)
```

### Root Cause
Gymnasium (new OpenAI Gym) returns 5 values from `env.step()`: `(obs, reward, terminated, truncated, info)`, while older Gym API returned 4: `(obs, reward, done, info)`.

### Solution
The fix is already implemented in `swarm.py` with backward compatibility:
```python
step_result = self.env.step(self._compute_actions())
if len(step_result) == 5:
    obs, rewards, terminated, truncated, infos = step_result
    dones = {i: terminated.get(i, False) or truncated.get(i, False)
            for i in range(self.num_drones)}
else:
    obs, rewards, dones, infos = step_result
```

## Running the Simulation

### With GUI (Recommended - uses NVIDIA GPU)
```bash
python main.py
# or with custom settings
python main.py --num 10
```

### Headless Mode (No GPU issues)
```bash
python main.py --headless
```

### Headless Mode with Custom Port
```bash
python main.py --headless --port 9000 --num 8
```

## System Requirements

### Verified Working Configuration
- **OS**: Ubuntu 24.04 (Noble)
- **GPU**: NVIDIA GeForce RTX 4060 Laptop + Intel Arc Graphics (hybrid)
- **Driver**: NVIDIA 580.95.05
- **Python**: 3.12
- **PyBullet**: 3.2.6
- **Gymnasium**: Latest (with 5-value step API)

### Required Packages
```bash
pip install pybullet gymnasium fastapi uvicorn requests numpy
```

### Graphics Libraries (Ubuntu)
```bash
sudo apt install libgl1-mesa-glx libegl1 libxext6 libx11-6
```

## Common Issues

### "NVIDIA driver not found"
If you don't have an NVIDIA GPU, use headless mode:
```bash
python main.py --headless
```

### "Port 8000 already in use"
Change the port:
```bash
python main.py --port 8001
```

### GUI window appears blank or frozen
Try running with explicit display:
```bash
DISPLAY=:0 python main.py
```

### Permission denied for NVIDIA device
Add your user to video group:
```bash
sudo usermod -aG video $USER
```
Then log out and back in.

## Alternative Solutions (If NVIDIA Fix Doesn't Work)

### 1. Use Headless Mode
The simulation works perfectly without GUI:
```bash
python main.py --headless
```

### 2. Build PyBullet from Source
For specific graphics configurations, building from source with custom flags may help:
```bash
git clone https://github.com/bulletphysics/bullet3.git
cd bullet3
./build_cmake_pybullet_double.sh
pip install -e .
```

### 3. Use Docker with GPU Passthrough
Run the simulation in a container with proper GL forwarding.

## Testing Your Setup

### Quick Test
```python
import os
os.environ['__NV_PRIME_RENDER_OFFLOAD'] = '1'
os.environ['__GLX_VENDOR_LIBRARY_NAME'] = 'nvidia'

import pybullet as p
client = p.connect(p.GUI)
print(f"Success! Client ID: {client}")
```

### API Test
```bash
# Start server
python main.py &

# Wait for startup
sleep 5

# Test API
curl http://localhost:8000/
```

## Support

For issues not covered here, check:
1. PyBullet GitHub issues: https://github.com/bulletphysics/bullet3/issues
2. Project issues: https://github.com/your-repo/AUS-Lab/issues
