#!/bin/bash
# Wrapper script to run PyBullet with X11/OpenGL fixes for Ubuntu 24.04

# Force specific GLX visual attributes
export XLIB_SKIP_ARGB_VISUALS=1

# Use indirect rendering if direct fails
export LIBGL_ALWAYS_INDIRECT=0

# Force specific Mesa driver
export MESA_LOADER_DRIVER_OVERRIDE=i915

# Set OpenGL version
export MESA_GL_VERSION_OVERRIDE=4.5
export MESA_GLSL_VERSION_OVERRIDE=450

# Run the simulation
python main.py "$@"
