import pytest
from simulation.swarm import SwarmWorld

def test_swarm_initialization():
    try:
        swarm = SwarmWorld(num_drones=1, gui=False, physics_hz=240, control_hz=60)
        assert swarm is not None
        assert swarm.num_drones == 1
        swarm.close()
    except Exception as e:
        pytest.fail(f"SwarmWorld initialization failed with an exception: {e}")
