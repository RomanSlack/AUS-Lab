// Drone state from the backend
export interface DroneState {
  id: number;
  pos: [number, number, number];
  vel: [number, number, number];
  yaw: number;
  battery: number;
  healthy: boolean;
}

// Full simulation state
export interface SimulationState {
  drones: DroneState[];
  timestamp: number;
}

// WebSocket message types
export interface StateMessage {
  type: 'state';
  payload: SimulationState;
}

export interface AckMessage {
  type: 'ack';
  payload: {
    success: boolean;
    message: string;
  };
}

export type ServerMessage = StateMessage | AckMessage;

// Command types
export type CommandAction =
  | 'takeoff'
  | 'land'
  | 'hover'
  | 'goto'
  | 'velocity'
  | 'formation'
  | 'spawn'
  | 'reset';

export interface CommandMessage {
  type: 'command';
  payload: {
    action: CommandAction;
    params: Record<string, unknown>;
  };
}

// Formation patterns
export type FormationPattern = 'circle' | 'line' | 'grid' | 'v';
