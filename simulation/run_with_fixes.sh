#!/bin/bash

# Script to run PyBullet simulation with NVIDIA rendering fixes for Ubuntu 24.04
# This addresses flickering issues on RTX 40-series cards with driver 570+

# Disable compositor effects that cause flickering
export KWIN_TRIPLE_BUFFER=1
export KWIN_OPENGL_INTERFACE=egl

# NVIDIA-specific OpenGL settings
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export __GL_SYNC_TO_VBLANK=0
export vblank_mode=0

# Force single-threaded rendering to avoid race conditions
export __GL_THREADED_OPTIMIZATIONS=0

# Use X11 sync to prevent tearing without flickering
export __GL_SYNC_DISPLAY_DEVICE=DP-0

# Run the simulation
python3 main.py "$@"
