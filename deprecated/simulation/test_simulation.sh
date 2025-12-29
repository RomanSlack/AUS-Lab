#!/bin/bash
# Quick test script to verify the simulation is working

echo "=== AUS-Lab Simulation Test ==="
echo ""

# Check NVIDIA GPU
echo "1. Checking for NVIDIA GPU..."
if nvidia-smi &>/dev/null; then
    echo "   ✓ NVIDIA GPU detected"
    nvidia-smi --query-gpu=name --format=csv,noheader
else
    echo "   ✗ No NVIDIA GPU found - GUI mode may not work"
    echo "   → Use --headless mode instead"
fi

echo ""
echo "2. Checking Python environment..."
if python -c "import pybullet, fastapi, numpy" 2>/dev/null; then
    echo "   ✓ Required packages installed"
else
    echo "   ✗ Missing packages - run: pip install -r requirements.txt"
    exit 1
fi

echo ""
echo "3. Testing PyBullet with NVIDIA..."
python -c "
import os
os.environ['__NV_PRIME_RENDER_OFFLOAD'] = '1'
os.environ['__GLX_VENDOR_LIBRARY_NAME'] = 'nvidia'
import pybullet as p
try:
    client = p.connect(p.DIRECT)  # Headless test first
    print('   ✓ PyBullet DIRECT mode works')
    p.disconnect()
except:
    print('   ✗ PyBullet connection failed')
    exit(1)
" 2>/dev/null

echo ""
echo "4. Starting simulation in background..."
python main.py --headless > /tmp/sim_test.log 2>&1 &
SIM_PID=$!
sleep 5

echo ""
echo "5. Testing API..."
if curl -s http://localhost:8000/ | grep -q "AUS-Lab"; then
    echo "   ✓ API is responding"
else
    echo "   ✗ API not responding"
    kill $SIM_PID 2>/dev/null
    exit 1
fi

echo ""
echo "6. Testing drone commands..."
RESPONSE=$(curl -s -X POST http://localhost:8000/takeoff \
  -H 'Content-Type: application/json' \
  -d '{"ids": ["all"], "altitude": 1.5}')

if echo "$RESPONSE" | grep -q "success"; then
    echo "   ✓ Takeoff command accepted"
else
    echo "   ✗ Takeoff command failed"
    kill $SIM_PID 2>/dev/null
    exit 1
fi

echo ""
echo "7. Cleaning up..."
kill $SIM_PID 2>/dev/null
sleep 2

echo ""
echo "==================================="
echo "✓ All tests passed!"
echo "==================================="
echo ""
echo "To start the simulation with GUI:"
echo "  python main.py"
echo ""
echo "To start headless mode:"
echo "  python main.py --headless"
echo ""
echo "API will be available at: http://localhost:8000"
