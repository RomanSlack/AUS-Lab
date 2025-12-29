import { SimulationCanvas } from './components/SimulationCanvas';
import { ControlPanel } from './components/ControlPanel';
import { ModelTest } from './components/ModelTest';
import { ChatPill } from './components/ChatPill';
import { DroneHUD } from './components/DroneHUD';
import { DroneCameraView } from './components/DroneCameraView';
import { ControlsOverlay } from './components/ControlsOverlay';
import { useWebSocket } from './hooks/useWebSocket';
import { useKeyboardControls } from './hooks/useKeyboardControls';
import './App.css';

function App() {
  // Check for test mode via URL param: ?test=model
  const params = new URLSearchParams(window.location.search);
  const testMode = params.get('test');

  // Show model test page if ?test=model
  if (testMode === 'model') {
    return <ModelTest />;
  }

  // Initialize WebSocket connection
  useWebSocket();

  // Initialize keyboard controls
  useKeyboardControls();

  return (
    <div className="app">
      <div className="canvas-container">
        <SimulationCanvas />
        <DroneHUD />
        <DroneCameraView />
        <ControlsOverlay />
        <ChatPill />
      </div>

      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>AUS-Lab</h1>
          <span>Autonomous Systems</span>
        </div>

        <ControlPanel />

        <div className="sidebar-footer">
          <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
            API Docs
          </a>
          {' | '}
          <a href="?test=model">Test Model</a>
        </div>
      </aside>
    </div>
  );
}

export default App;
