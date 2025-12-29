import { create } from 'zustand';
import type { DroneState } from '../types/simulation';

export interface KeyboardState {
  w: boolean;
  a: boolean;
  s: boolean;
  d: boolean;
  space: boolean;
  shift: boolean;
  q: boolean;
  e: boolean;
}

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

  // Selected drone for control
  selectedDroneId: number | null;
  setSelectedDroneId: (id: number | null) => void;

  // Keyboard state for manual control
  keys: KeyboardState;
  setKey: (key: keyof KeyboardState, pressed: boolean) => void;

  // Manual control mode
  manualControlActive: boolean;
  setManualControlActive: (active: boolean) => void;

  // Waypoint (click-to-go target)
  waypoint: [number, number, number] | null;
  setWaypoint: (waypoint: [number, number, number] | null) => void;

  // Monitor mode toggle
  monitorMode: boolean;
  setMonitorMode: (enabled: boolean) => void;

  // FPV camera texture data
  fpvTexture: Uint8Array | null;
  setFpvTexture: (texture: Uint8Array | null) => void;

  // Helper to get selected drone data
  getSelectedDrone: () => DroneState | null;
}

export const useSimulationStore = create<SimulationStore>((set, get) => ({
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

  // Keyboard state
  keys: {
    w: false,
    a: false,
    s: false,
    d: false,
    space: false,
    shift: false,
    q: false,
    e: false,
  },
  setKey: (key, pressed) =>
    set((state) => ({
      keys: { ...state.keys, [key]: pressed },
    })),

  // Manual control mode
  manualControlActive: false,
  setManualControlActive: (active) => set({ manualControlActive: active }),

  // Waypoint
  waypoint: null,
  setWaypoint: (waypoint) => set({ waypoint }),

  // Monitor mode
  monitorMode: false,
  setMonitorMode: (enabled) => set({ monitorMode: enabled }),

  // FPV texture
  fpvTexture: null,
  setFpvTexture: (texture) => set({ fpvTexture: texture }),

  // Get selected drone data
  getSelectedDrone: () => {
    const { drones, selectedDroneId } = get();
    if (selectedDroneId === null) return null;
    return drones.find((d) => d.id === selectedDroneId) || null;
  },
}));
