#!/usr/bin/env python3
"""
Simple test to check if PyBullet mouse/keyboard events work at all.
"""

import os

# CRITICAL: Set NVIDIA environment variables BEFORE importing pybullet
os.environ['__NV_PRIME_RENDER_OFFLOAD'] = '1'
os.environ['__GLX_VENDOR_LIBRARY_NAME'] = 'nvidia'

import pybullet as p
import time

# Connect to GUI
print("Connecting to PyBullet GUI...")
client = p.connect(p.GUI)
print(f"Connected with client ID: {client}")

# Enable mouse picking
p.configureDebugVisualizer(p.COV_ENABLE_MOUSE_PICKING, 1, physicsClientId=client)
print("Mouse picking enabled")

# Load a simple ground plane (optional, skip if not found)
try:
    import pybullet_data
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.loadURDF("plane.urdf", physicsClientId=client)
    print("Ground plane loaded")
except:
    print("Skipping ground plane (not critical for test)")

print("\n" + "="*60)
print("TEST: Press any key or click mouse in PyBullet window")
print("="*60)
print("Checking for events for 30 seconds...")
print("You should see output when you press keys or click\n")

start_time = time.time()
last_event_time = time.time()

while time.time() - start_time < 30:
    # Check keyboard events
    kb_events = p.getKeyboardEvents(physicsClientId=client)
    if len(kb_events) > 0:
        print(f"[KEYBOARD] Events detected: {kb_events}")
        last_event_time = time.time()

    # Check mouse events
    mouse_events = p.getMouseEvents(physicsClientId=client)
    if len(mouse_events) > 0:
        print(f"[MOUSE] Events detected: {len(mouse_events)} events")
        for event in mouse_events[:3]:  # Print first 3
            print(f"  Event: {event}")
        last_event_time = time.time()

    time.sleep(0.05)  # 20Hz polling

print("\n" + "="*60)
print(f"Test complete. Last event was {time.time() - last_event_time:.1f}s ago")
print("="*60)

p.disconnect(physicsClientId=client)
