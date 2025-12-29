import { useSimulationStore } from '../store/simulationStore';

export function ControlsOverlay() {
  const { selectedDroneId, keys } = useSimulationStore();

  if (selectedDroneId === null) return null;

  return (
    <div className="controls-overlay">
      <div className="controls-title">Manual Control</div>

      <div className="controls-grid">
        <div className="control-key empty" />
        <div className={`control-key ${keys.w ? 'active' : ''}`}>W</div>
        <div className="control-key empty" />

        <div className={`control-key ${keys.a ? 'active' : ''}`}>A</div>
        <div className={`control-key ${keys.s ? 'active' : ''}`}>S</div>
        <div className={`control-key ${keys.d ? 'active' : ''}`}>D</div>
      </div>

      <div className="controls-extra">
        <div className={`control-key ${keys.space ? 'active' : ''}`} style={{ width: '48px' }}>
          ␣
        </div>
        <div className={`control-key ${keys.shift ? 'active' : ''}`} style={{ width: '48px' }}>
          ⇧
        </div>
      </div>

      <div className="control-label">Space: Up / Shift: Down</div>

      <div className="controls-extra" style={{ marginTop: '8px' }}>
        <div className={`control-key ${keys.q ? 'active' : ''}`}>Q</div>
        <div className={`control-key ${keys.e ? 'active' : ''}`}>E</div>
      </div>

      <div className="control-label">Q/E: Rotate</div>
    </div>
  );
}
