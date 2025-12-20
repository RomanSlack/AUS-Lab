import { create } from 'zustand';
import type { DroneState } from '../types/simulation';

interface SimulationStore {
  // Connection state
  connected: boolean;
  setConnected: (connected: boolean) => void;

  // Drone state
  drones: DroneState[];
  timestamp: number;
  updateState: (drones: DroneState[], timestamp: number) => void;

  // WebSocket instance
  ws: WebSocket | null;
  setWs: (ws: WebSocket | null) => void;

  // Selected drone for details view
  selectedDroneId: number | null;
  setSelectedDroneId: (id: number | null) => void;

  // Waypoint (click-to-go target)
  waypoint: [number, number, number] | null;
  setWaypoint: (waypoint: [number, number, number] | null) => void;

  // Monitor mode toggle
  monitorMode: boolean;
  setMonitorMode: (enabled: boolean) => void;
}

export const useSimulationStore = create<SimulationStore>((set) => ({
  // Connection
  connected: false,
  setConnected: (connected) => set({ connected }),

  // Drone state
  drones: [],
  timestamp: 0,
  updateState: (drones, timestamp) => set({ drones, timestamp }),

  // WebSocket
  ws: null,
  setWs: (ws) => set({ ws }),

  // Selection
  selectedDroneId: null,
  setSelectedDroneId: (id) => set({ selectedDroneId: id }),

  // Waypoint
  waypoint: null,
  setWaypoint: (waypoint) => set({ waypoint }),

  // Monitor mode
  monitorMode: false,
  setMonitorMode: (enabled) => set({ monitorMode: enabled }),
}));
