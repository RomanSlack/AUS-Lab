import { useSimulationStore } from '../store/simulationStore';
import { snapCameraToPosition } from './SimulationCanvas';

export function StateDisplay() {
  const { drones, timestamp, selectedDroneId, setSelectedDroneId } = useSimulationStore();

  const selectedDrone = selectedDroneId !== null ? drones.find((d) => d.id === selectedDroneId) : null;

  const handleDroneClick = (droneId: number) => {
    setSelectedDroneId(droneId === selectedDroneId ? null : droneId);
  };

  const handleDroneDoubleClick = (drone: typeof drones[0]) => {
    // Snap camera to drone position
    snapCameraToPosition(drone.pos[0], drone.pos[1], drone.pos[2]);
    setSelectedDroneId(drone.id);
  };

  return (
    <div className="state-display">
      <h2>Drone States</h2>
      <div className="timestamp">
        Time: {timestamp.toFixed(2)}s
      </div>
      <div className="drone-list-hint" style={{ fontSize: '10px', color: '#888', marginBottom: '4px' }}>
        Double-click to focus camera
      </div>

      <div className="drone-list">
        {drones.map((drone) => (
          <div
            key={drone.id}
            className={`drone-item ${selectedDroneId === drone.id ? 'selected' : ''} ${
              drone.healthy ? 'healthy' : 'unhealthy'
            }`}
            onClick={() => handleDroneClick(drone.id)}
            onDoubleClick={() => handleDroneDoubleClick(drone)}
            style={{ cursor: 'pointer' }}
          >
            <span className="drone-id">#{drone.id}</span>
            <span className="drone-health">{drone.healthy ? '●' : '○'}</span>
            <span className="drone-battery">{drone.battery.toFixed(0)}%</span>
          </div>
        ))}
      </div>

      {selectedDrone && (
        <div className="drone-details">
          <h3>Drone #{selectedDrone.id}</h3>
          <div className="detail-row">
            <span>Position:</span>
            <span>
              ({selectedDrone.pos[0].toFixed(2)}, {selectedDrone.pos[1].toFixed(2)},{' '}
              {selectedDrone.pos[2].toFixed(2)})
            </span>
          </div>
          <div className="detail-row">
            <span>Velocity:</span>
            <span>
              ({selectedDrone.vel[0].toFixed(2)}, {selectedDrone.vel[1].toFixed(2)},{' '}
              {selectedDrone.vel[2].toFixed(2)})
            </span>
          </div>
          <div className="detail-row">
            <span>Yaw:</span>
            <span>{((selectedDrone.yaw * 180) / Math.PI).toFixed(1)}°</span>
          </div>
          <div className="detail-row">
            <span>Battery:</span>
            <span>{selectedDrone.battery.toFixed(1)}%</span>
          </div>
          <div className="detail-row">
            <span>Status:</span>
            <span className={selectedDrone.healthy ? 'healthy' : 'unhealthy'}>
              {selectedDrone.healthy ? 'Healthy' : 'Unhealthy'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
