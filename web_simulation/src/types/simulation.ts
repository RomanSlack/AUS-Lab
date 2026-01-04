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

// ============================================================================
// Terrain Types
// ============================================================================

export interface TerrainMeshData {
  positions: string;    // Base64-encoded Float32 array
  normals: string;      // Base64-encoded Float32 array
  uvs: string;          // Base64-encoded Float32 array
  indices: string;      // Base64-encoded Uint32 array
  width: number;
  height: number;
  minElevation: number;
  maxElevation: number;
  boundsMin: [number, number, number];
  boundsMax: [number, number, number];
  vertexCount: number;
  indexCount: number;
}

export interface TerrainTextureData {
  data: string;         // Base64-encoded JPEG
  width: number;
  height: number;
}

export interface TerrainLocation {
  centerLat: number;
  centerLng: number;
  areaSizeMeters: number;
}

export interface TerrainCoordinateMapping {
  geoOriginLat: number;
  geoOriginLng: number;
  metersPerUnit: number;
}

export interface TerrainLoadResponse {
  success: boolean;
  mesh: TerrainMeshData;
  texture: TerrainTextureData;
  location: TerrainLocation;
  coordinateMapping: TerrainCoordinateMapping;
}

export interface TerrainStatusResponse {
  configured: boolean;
  cacheEnabled: boolean;
  cacheDir: string;
  message: string;
}

// Preset locations for quick selection
export interface TerrainPreset {
  name: string;
  lat: number;
  lng: number;
  sizeMeters: number;
  description: string;
}

export const TERRAIN_PRESETS: TerrainPreset[] = [
  { name: 'Emerald Bay (Tahoe)', lat: 38.9533, lng: -120.1100, sizeMeters: 1000, description: 'Steep cliffs at Lake Tahoe' },
  { name: 'Grand Canyon', lat: 36.0544, lng: -112.1401, sizeMeters: 1000, description: 'South Rim viewpoint' },
  { name: 'Mt Rainier', lat: 46.8523, lng: -121.7603, sizeMeters: 1000, description: 'Volcanic peak, Washington' },
  { name: 'Yosemite Valley', lat: 37.7456, lng: -119.5936, sizeMeters: 1000, description: 'Granite cliffs and waterfalls' },
  { name: 'Matterhorn', lat: 45.9763, lng: 7.6586, sizeMeters: 1000, description: 'Iconic Swiss Alps peak' },
  { name: 'Kilauea Crater', lat: 19.4069, lng: -155.2834, sizeMeters: 1000, description: 'Active Hawaiian volcano' },
  { name: 'Half Dome', lat: 37.7459, lng: -119.5332, sizeMeters: 1000, description: 'Yosemite granite dome' },
  { name: 'Zion Canyon', lat: 37.2982, lng: -112.9487, sizeMeters: 1000, description: 'Red rock canyon, Utah' },
];
