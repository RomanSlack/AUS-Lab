import { useState, useEffect } from 'react';
import { useCommands } from '../hooks/useCommands';
import { useSimulationStore } from '../store/simulationStore';
import type { FormationPattern } from '../types/simulation';

export function ControlPanel() {
  const { takeoff, land, hover, formation, spawn, reset, setSpeed } = useCommands();
  const { connected, drones, monitorMode, setMonitorMode } = useSimulationStore();

  const [altitude, setAltitude] = useState(1.5);
  const [droneCount, setDroneCount] = useState(50);
  const [formationRadius, setFormationRadius] = useState(2.0);
  const [speed, setSpeedValue] = useState(1.0);

  // Send initial speed when connected
  useEffect(() => {
    if (connected) {
      setSpeed(speed);
    }
  }, [connected]);

  const handleSpeedChange = (newSpeed: number) => {
    setSpeedValue(newSpeed);
    setSpeed(newSpeed);
  };

  const handleFormation = (pattern: FormationPattern) => {
    const center: [number, number, number] = [0, 0, altitude];
    if (pattern === 'circle') {
      formation(pattern, center, { radius: formationRadius });
    } else {
      formation(pattern, center, { spacing: 0.8 });
    }
  };

  return (
    <div className="control-panel">
      <h2>Swarm Control</h2>

      <div className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
        {connected ? 'Connected' : 'Disconnected'}
      </div>

      <section>
        <h3>Basic Commands</h3>
        <div className="button-group">
          <button onClick={() => takeoff(['all'], altitude)} disabled={!connected}>
            Takeoff
          </button>
          <button onClick={() => land(['all'])} disabled={!connected}>
            Land
          </button>
          <button onClick={() => hover(['all'])} disabled={!connected}>
            Hover
          </button>
        </div>

        <div className="slider-group">
          <label>
            Altitude: {altitude.toFixed(1)}m
            <input
              type="range"
              min={0.5}
              max={5}
              step={0.1}
              value={altitude}
              onChange={(e) => setAltitude(Number(e.target.value))}
            />
          </label>
        </div>
      </section>

      <section>
        <h3>Formations</h3>
        <div className="button-group formations">
          <button onClick={() => handleFormation('circle')} disabled={!connected}>
            Circle
          </button>
          <button onClick={() => handleFormation('line')} disabled={!connected}>
            Line
          </button>
          <button onClick={() => handleFormation('grid')} disabled={!connected}>
            Grid
          </button>
          <button onClick={() => handleFormation('v')} disabled={!connected}>
            V-Shape
          </button>
        </div>

        <div className="slider-group">
          <label>
            Radius: {formationRadius.toFixed(1)}m
            <input
              type="range"
              min={1}
              max={5}
              step={0.5}
              value={formationRadius}
              onChange={(e) => setFormationRadius(Number(e.target.value))}
            />
          </label>
        </div>
      </section>

      <section>
        <h3>Swarm Management</h3>
        <div className="spawn-controls">
          <input
            type="number"
            min={1}
            value={droneCount}
            onChange={(e) => setDroneCount(Number(e.target.value))}
          />
          <button onClick={() => spawn(droneCount)} disabled={!connected}>
            Spawn
          </button>
        </div>
        <button className="danger" onClick={() => reset()} disabled={!connected}>
          Reset Simulation
        </button>
      </section>

      <section>
        <h3>Drone Velocity</h3>
        <div className="slider-group">
          <label>
            <div className="speed-display">
              <span>{speed.toFixed(1)}x</span>
              <span className="speed-units">
                {(speed * 2).toFixed(1)} m/s | {(speed * 2 * 2.237).toFixed(1)} mph
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={20}
              step={0.5}
              value={speed}
              onChange={(e) => handleSpeedChange(Number(e.target.value))}
            />
          </label>
        </div>
      </section>

      <section>
        <h3>Click Mode</h3>
        <div className="button-group">
          <button
            className={!monitorMode ? 'active' : ''}
            onClick={() => setMonitorMode(false)}
            disabled={!connected}
          >
            Waypoint
          </button>
          <button
            className={monitorMode ? 'active monitor' : ''}
            onClick={() => setMonitorMode(true)}
            disabled={!connected}
          >
            Monitor
          </button>
        </div>
        <p className="mode-hint">
          {monitorMode
            ? 'Click to set surveillance orbit point'
            : 'Click to send drones to location'}
        </p>
      </section>

      <section>
        <h3>Status</h3>
        <div className="status-info">
          <span>Drones: {drones.length}</span>
          <span>
            Healthy: {drones.filter((d) => d.healthy).length}/{drones.length}
          </span>
        </div>
      </section>
    </div>
  );
}
