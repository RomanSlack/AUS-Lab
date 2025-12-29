import { useSimulationStore } from '../store/simulationStore';

function getBatteryClass(battery: number): string {
  if (battery < 20) return 'low';
  if (battery < 50) return 'mid';
  return '';
}

export function DroneHUD() {
  const { drones, selectedDroneId, setSelectedDroneId } = useSimulationStore();
  const selectedDrone = drones.find((d) => d.id === selectedDroneId);

  const handleDroneClick = (id: number) => {
    setSelectedDroneId(selectedDroneId === id ? null : id);
  };

  const healthyCount = drones.filter((d) => d.healthy).length;

  return (
    <div className="drone-hud">
      <div className="hud-panel">
        <div className="hud-header">
          <span className="hud-title">Fleet Status</span>
          <span className="hud-count">
            {healthyCount}/{drones.length}
          </span>
        </div>

        <div className="hud-drone-grid">
          {drones.map((drone) => (
            <div
              key={drone.id}
              className={`hud-drone-item ${
                selectedDroneId === drone.id ? 'selected' : ''
              } ${!drone.healthy ? 'unhealthy' : ''}`}
              onClick={() => handleDroneClick(drone.id)}
            >
              <span className="hud-drone-id">{drone.id.toString().padStart(2, '0')}</span>
              <span className={`hud-drone-battery ${getBatteryClass(drone.battery)}`}>
                {drone.battery.toFixed(0)}%
              </span>
            </div>
          ))}
        </div>

        {selectedDrone && (
          <div className="hud-selected-info">
            <div className="hud-selected-header">
              <span className="hud-selected-title">Drone {selectedDrone.id}</span>
              <span className="hud-controls-hint">WASD to fly</span>
            </div>

            <div className="hud-stat-row">
              <span className="hud-stat-label">Position</span>
              <span className="hud-stat-value">
                {selectedDrone.pos[0].toFixed(1)}, {selectedDrone.pos[1].toFixed(1)},{' '}
                {selectedDrone.pos[2].toFixed(1)}
              </span>
            </div>

            <div className="hud-stat-row">
              <span className="hud-stat-label">Altitude</span>
              <span className="hud-stat-value">{selectedDrone.pos[2].toFixed(2)}m</span>
            </div>

            <div className="hud-stat-row">
              <span className="hud-stat-label">Velocity</span>
              <span className="hud-stat-value">
                {Math.sqrt(
                  selectedDrone.vel[0] ** 2 +
                    selectedDrone.vel[1] ** 2 +
                    selectedDrone.vel[2] ** 2
                ).toFixed(1)}{' '}
                m/s
              </span>
            </div>

            <div className="hud-stat-row">
              <span className="hud-stat-label">Heading</span>
              <span className="hud-stat-value">
                {((selectedDrone.yaw * 180) / Math.PI).toFixed(0)}°
              </span>
            </div>

            <div className="hud-stat-row">
              <span className="hud-stat-label">Battery</span>
              <span className={`hud-stat-value ${getBatteryClass(selectedDrone.battery)}`}>
                {selectedDrone.battery.toFixed(1)}%
              </span>
            </div>

            <div className="hud-stat-row">
              <span className="hud-stat-label">Status</span>
              <span className={`hud-stat-value ${selectedDrone.healthy ? 'healthy' : 'unhealthy'}`}>
                {selectedDrone.healthy ? 'Operational' : 'Fault'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
