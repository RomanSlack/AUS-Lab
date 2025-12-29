import React, { useState, useEffect } from 'react';
import './App.css';
import Simulation from './Simulation';

function App() {
  const [command, setCommand] = useState('');
  const [simulationState, setSimulationState] = useState(null);

  const handleSendCommand = async () => {
    try {
      const response = await fetch('http://localhost:8001/command', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ command }),
      });
      const data = await response.json();
      console.log('Command response:', data);
    } catch (error) {
      console.error('Error sending command:', error);
    }
  };

  const handleEnableHivemind = async () => {
    try {
      const response = await fetch('http://localhost:8000/hivemind/enable', {
        method: 'POST',
      });
      const data = await response.json();
      console.log('Enable hivemind response:', data);
    } catch (error) {
      console.error('Error enabling hivemind:', error);
    }
  };

  const handleDisableHivemind = async () => {
    try {
      const response = await fetch('http://localhost:8000/hivemind/disable', {
        method: 'POST',
      });
      const data = await response.json();
      console.log('Disable hivemind response:', data);
    } catch (error) {
      console.error('Error disabling hivemind:', error);
    }
  };

  const handleMoveHivemind = async () => {
    try {
      const response = await fetch('http://localhost:8000/hivemind/move', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          position: [2, 2, 2],
          yaw: 0.5,
          scale: 1.5,
        }),
      });
      const data = await response.json();
      console.log('Move hivemind response:', data);
    } catch (error) {
      console.error('Error moving hivemind:', error);
    }
  };

  useEffect(() => {
    const fetchState = async () => {
      try {
        const response = await fetch('http://localhost:8000/state');
        const data = await response.json();
        setSimulationState(data);
      } catch (error) {
        console.error('Error fetching state:', error);
      }
    };

    const interval = setInterval(fetchState, 1000); // Fetch state every second

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>AUS-Lab</h1>
      </header>
      <main>
        <div className="simulation-container">
          <Simulation simulationState={simulationState} />
        </div>
        <div className="command-container">
          <input
            type="text"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder="Enter a command..."
          />
          <button onClick={handleSendCommand}>Send</button>
          <button onClick={handleEnableHivemind}>Enable Hivemind</button>
          <button onClick={handleDisableHivemind}>Disable Hivemind</button>
          <button onClick={handleMoveHivemind}>Move Hivemind</button>
        </div>
      </main>
    </div>
  );
}

export default App;
