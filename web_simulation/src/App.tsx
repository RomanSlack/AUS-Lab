import { SimulationCanvas } from './components/SimulationCanvas';
import { ControlPanel } from './components/ControlPanel';
import { StateDisplay } from './components/StateDisplay';
import { ModelTest } from './components/ModelTest';
import { useWebSocket } from './hooks/useWebSocket';
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

  return (
    <div className="app">
      <div className="canvas-container">
        <SimulationCanvas />
      </div>

      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>AUS-Lab</h1>
          <span>Drone Simulation</span>
        </div>

        <ControlPanel />
        <StateDisplay />

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
