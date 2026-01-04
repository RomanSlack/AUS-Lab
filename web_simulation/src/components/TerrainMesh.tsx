import { useMemo, useRef, useEffect } from 'react';
import * as THREE from 'three';
import { useSimulationStore } from '../store/simulationStore';
import type { TerrainMeshData, TerrainTextureData } from '../types/simulation';

/**
 * Decode base64-encoded binary data to typed array
 */
function decodeBase64ToFloat32(base64: string): Float32Array {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return new Float32Array(bytes.buffer);
}

function decodeBase64ToUint32(base64: string): Uint32Array {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return new Uint32Array(bytes.buffer);
}

/**
 * Create Three.js BufferGeometry from terrain mesh data
 */
function createTerrainGeometry(meshData: TerrainMeshData): THREE.BufferGeometry {
  const geometry = new THREE.BufferGeometry();

  // Decode binary data
  const positions = decodeBase64ToFloat32(meshData.positions);
  const normals = decodeBase64ToFloat32(meshData.normals);
  const uvs = decodeBase64ToFloat32(meshData.uvs);
  const indices = decodeBase64ToUint32(meshData.indices);

  // Set attributes
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
  geometry.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
  geometry.setIndex(new THREE.BufferAttribute(indices, 1));

  // Compute bounding sphere for frustum culling
  geometry.computeBoundingSphere();

  return geometry;
}

/**
 * Create Three.js texture from base64 JPEG data
 */
function createTerrainTexture(textureData: TerrainTextureData): THREE.Texture {
  const texture = new THREE.Texture();

  // Create image from base64 data
  const img = new Image();
  img.onload = () => {
    texture.image = img;
    texture.needsUpdate = true;
  };
  img.src = `data:image/jpeg;base64,${textureData.data}`;

  // Configure texture
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.colorSpace = THREE.SRGBColorSpace;

  return texture;
}

interface TerrainMeshProps {
  // Optional Y offset to position terrain (default centers at origin)
  yOffset?: number;
}

/**
 * Three.js component that renders terrain mesh with satellite texture.
 *
 * Reads terrain data from Zustand store and creates geometry + texture.
 * The mesh is positioned so drones can fly over it naturally.
 */
export function TerrainMesh({ yOffset = 0 }: TerrainMeshProps) {
  const terrain = useSimulationStore((state) => state.terrain);
  const meshRef = useRef<THREE.Mesh>(null);
  const textureRef = useRef<THREE.Texture | null>(null);

  // Create geometry from terrain data
  const geometry = useMemo(() => {
    if (!terrain) return null;
    return createTerrainGeometry(terrain.mesh);
  }, [terrain]);

  // Create texture from satellite imagery
  const texture = useMemo(() => {
    if (!terrain) return null;
    const tex = createTerrainTexture(terrain.texture);
    textureRef.current = tex;
    return tex;
  }, [terrain]);

  // Cleanup texture on unmount
  useEffect(() => {
    return () => {
      if (textureRef.current) {
        textureRef.current.dispose();
      }
    };
  }, []);

  // Cleanup geometry on unmount or when terrain changes
  useEffect(() => {
    return () => {
      if (geometry) {
        geometry.dispose();
      }
    };
  }, [geometry]);

  if (!terrain || !geometry || !texture) {
    return null;
  }

  // The mesh is already centered at origin from the backend
  // Y (up) contains elevation, X and Z are horizontal
  // We add a small Y offset to lift the terrain if needed

  return (
    <mesh
      ref={meshRef}
      geometry={geometry}
      position={[0, yOffset, 0]}
      receiveShadow
      castShadow
    >
      <meshStandardMaterial
        map={texture}
        side={THREE.FrontSide}
        roughness={0.9}
        metalness={0.0}
      />
    </mesh>
  );
}

/**
 * Simplified terrain placeholder when no terrain is loaded.
 * Shows the current flat ground with a hint that terrain can be loaded.
 */
export function TerrainPlaceholder() {
  const terrain = useSimulationStore((state) => state.terrain);

  // Don't show placeholder if terrain is loaded
  if (terrain) return null;

  return (
    <mesh
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, 0, 0]}
      receiveShadow
    >
      <planeGeometry args={[50, 50]} />
      <meshStandardMaterial color="#2a4a2a" roughness={0.9} metalness={0.1} />
    </mesh>
  );
}

/**
 * Information display about loaded terrain
 */
export function TerrainInfo() {
  const terrain = useSimulationStore((state) => state.terrain);

  if (!terrain) return null;

  const { location, mesh, coordinateMapping } = terrain;

  return (
    <div style={{
      position: 'absolute',
      bottom: '10px',
      left: '10px',
      background: 'rgba(0, 0, 0, 0.7)',
      color: 'white',
      padding: '8px 12px',
      borderRadius: '4px',
      fontSize: '12px',
      fontFamily: 'monospace',
      pointerEvents: 'none',
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>Terrain Loaded</div>
      <div>Location: {location.centerLat.toFixed(4)}, {location.centerLng.toFixed(4)}</div>
      <div>Area: {location.areaSizeMeters}m x {location.areaSizeMeters}m</div>
      <div>Elevation: {mesh.minElevation.toFixed(0)}m - {mesh.maxElevation.toFixed(0)}m</div>
      <div>Scale: 1:{coordinateMapping.metersPerUnit.toFixed(0)}</div>
    </div>
  );
}
