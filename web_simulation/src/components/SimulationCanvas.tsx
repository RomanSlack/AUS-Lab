import { useRef, useEffect } from 'react';
import { Canvas, ThreeEvent, useThree } from '@react-three/fiber';
import { OrbitControls, Grid, Environment, Stats } from '@react-three/drei';
import * as THREE from 'three';
import { DroneSwarm } from './DroneSwarm';
import { DroneFPVCamera } from './DroneFPVCamera';
import { TerrainMesh } from './TerrainMesh';
import { FlyCamera } from './FlyCamera';
import { useSimulationStore } from '../store/simulationStore';
import { useCommands } from '../hooks/useCommands';
import type { OrbitControls as OrbitControlsType } from 'three-stdlib';

function WaypointMarker({ position, isMonitor }: { position: [number, number, number]; isMonitor: boolean }) {
  // Convert from PyBullet coords (x, y, z) to Three.js (x, z, -y)
  const threePos: [number, number, number] = [position[0], position[2], -position[1]];

  // Green for waypoint, orange for monitor mode
  const color = isMonitor ? '#ff8800' : '#00ff88';

  return (
    <group position={threePos}>
      {/* Vertical beam */}
      <mesh position={[0, 0.5, 0]}>
        <cylinderGeometry args={[0.03, 0.03, 1, 8]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.5} />
      </mesh>
      {/* Top sphere */}
      <mesh position={[0, 1, 0]}>
        <sphereGeometry args={[0.1, 16, 16]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
      </mesh>
      {/* Ground ring - larger for monitor mode */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
        <ringGeometry args={isMonitor ? [0.8, 1.0, 32] : [0.2, 0.3, 32]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.5} side={THREE.DoubleSide} />
      </mesh>
      {/* Extra orbit rings for monitor mode */}
      {isMonitor && (
        <>
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
            <ringGeometry args={[1.8, 2.0, 32]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} side={THREE.DoubleSide} transparent opacity={0.5} />
          </mesh>
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
            <ringGeometry args={[2.8, 3.0, 32]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.2} side={THREE.DoubleSide} transparent opacity={0.3} />
          </mesh>
        </>
      )}
    </group>
  );
}

function ClickableGround({ onGroundClick }: { onGroundClick: (point: THREE.Vector3) => void }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const terrain = useSimulationStore((state) => state.terrain);

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    if (event.point) {
      onGroundClick(event.point);
    }
  };

  // Scale click plane based on terrain size
  const isRealisticScale = terrain?.coordinateMapping?.metersPerUnit === 1;
  const planeSize = isRealisticScale ? 5000 : 50;

  // If terrain is loaded, we only need an invisible click plane
  // The terrain mesh provides the visual, this provides click detection
  if (terrain) {
    // Position click plane at the average terrain Y position
    const avgY = terrain.mesh.boundsMin && terrain.mesh.boundsMax
      ? (terrain.mesh.boundsMin[1] + terrain.mesh.boundsMax[1]) / 2
      : 0;

    return (
      <mesh
        ref={meshRef}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, avgY + 0.1, 0]}
        onClick={handleClick}
      >
        <planeGeometry args={[planeSize, planeSize]} />
        <meshBasicMaterial transparent opacity={0} />
      </mesh>
    );
  }

  return (
    <mesh
      ref={meshRef}
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, 0, 0]}
      receiveShadow
      onClick={handleClick}
    >
      <planeGeometry args={[planeSize, planeSize]} />
      <meshStandardMaterial color="#2a4a2a" roughness={0.9} metalness={0.1} />
    </mesh>
  );
}

// Store refs for camera snapping
let globalOrbitControls: OrbitControlsType | null = null;
let globalCamera: THREE.Camera | null = null;

// Function to snap camera to a position (called from StateDisplay)
export function snapCameraToPosition(x: number, y: number, z: number) {
  // Convert PyBullet coords to Three.js
  const threeX = x;
  const threeY = z;  // PyBullet Z -> Three.js Y
  const threeZ = -y; // PyBullet Y -> Three.js -Z

  const offset = 10; // meters - close to drone

  if (globalCamera) {
    // Position camera near the drone
    globalCamera.position.set(
      threeX + offset,
      threeY + offset,
      threeZ + offset
    );

    // Look at the drone
    globalCamera.lookAt(threeX, threeY, threeZ);

    console.log('[Camera] Snapped to position:', { x: threeX, y: threeY, z: threeZ });
  }

  if (globalOrbitControls) {
    // Also update orbit controls target
    globalOrbitControls.target.set(threeX, threeY, threeZ);
    globalOrbitControls.update();
  }
}

// Component to capture camera ref
function CameraCapture() {
  const { camera } = useThree();

  useEffect(() => {
    globalCamera = camera;
    return () => {
      globalCamera = null;
    };
  }, [camera]);

  return null;
}

function Scene() {
  const { drones, waypoint, setWaypoint, monitorMode, terrain, cameraMode } = useSimulationStore();
  const { waypoint: sendWaypoint, monitor: sendMonitor } = useCommands();
  const controlsRef = useRef<OrbitControlsType>(null);

  // Store controls ref globally for external access
  useEffect(() => {
    if (controlsRef.current) {
      globalOrbitControls = controlsRef.current;
    }
    return () => {
      globalOrbitControls = null;
    };
  }, [cameraMode]);

  // Calculate terrain-aware parameters
  const isRealisticScale = terrain?.coordinateMapping?.metersPerUnit === 1;
  const terrainYCenter = terrain?.mesh?.boundsMin && terrain?.mesh?.boundsMax
    ? (terrain.mesh.boundsMin[1] + terrain.mesh.boundsMax[1]) / 2
    : 0;

  const handleGroundClick = (point: THREE.Vector3) => {
    // Convert Three.js coords (x, y, z) to PyBullet (x, -z, y)
    // Three.js: x-right, y-up, z-towards camera
    // PyBullet: x-right, y-forward, z-up
    const pybulletX = point.x;
    const pybulletY = -point.z;
    // For realistic scale, hover above terrain elevation
    const pybulletZ = isRealisticScale ? terrainYCenter + 50 : 1.5;

    setWaypoint([pybulletX, pybulletY, pybulletZ]);

    if (monitorMode) {
      console.log(`[Monitor] Surveillance mode at (${pybulletX.toFixed(2)}, ${pybulletY.toFixed(2)}, ${pybulletZ.toFixed(2)})`);
      sendMonitor(pybulletX, pybulletY, pybulletZ);
    } else {
      console.log(`[Waypoint] Go to (${pybulletX.toFixed(2)}, ${pybulletY.toFixed(2)}, ${pybulletZ.toFixed(2)})`);
      sendWaypoint(pybulletX, pybulletY, pybulletZ);
    }
  };

  // Scale parameters based on terrain
  const lightPos: [number, number, number] = isRealisticScale
    ? [500, 1000, 500]
    : [10, 20, 10];
  const shadowCameraSize = isRealisticScale ? 2000 : 20;

  return (
    <>
      {/* Additional lighting for shadows (HDRI provides main lighting) */}
      <directionalLight
        position={lightPos}
        intensity={0.5}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-far={isRealisticScale ? 3000 : 50}
        shadow-camera-left={-shadowCameraSize}
        shadow-camera-right={shadowCameraSize}
        shadow-camera-top={shadowCameraSize}
        shadow-camera-bottom={-shadowCameraSize}
      />

      {/* Terrain (if loaded) */}
      <TerrainMesh />

      {/* Clickable Ground (invisible when terrain loaded) */}
      <ClickableGround onGroundClick={handleGroundClick} />

      {/* Waypoint marker */}
      {waypoint && <WaypointMarker position={waypoint} isMonitor={monitorMode} />}

      {/* Grid - hide for realistic scale terrain (too fine), adjust for other cases */}
      {!isRealisticScale && (
        <Grid
          position={[0, terrain ? terrainYCenter + 0.01 : 0.01, 0]}
          args={[50, 50]}
          cellSize={1}
          cellThickness={0.5}
          cellColor="#444"
          sectionSize={5}
          sectionThickness={1}
          sectionColor="#666"
          fadeDistance={40}
          infiniteGrid
        />
      )}

      {/* Drones */}
      <DroneSwarm drones={drones} />

      {/* FPV Camera for selected drone */}
      <DroneFPVCamera />

      {/* Camera capture for snap-to-drone */}
      <CameraCapture />

      {/* Camera controls - switch between orbit and fly mode */}
      {cameraMode === 'orbit' ? (
        <OrbitControls
          ref={controlsRef}
          enableDamping
          dampingFactor={0.05}
          minDistance={isRealisticScale ? 5 : 2}
          maxDistance={isRealisticScale ? 5000 : 50}
          maxPolarAngle={Math.PI / 2.1}
          target={[0, isRealisticScale ? terrainYCenter : 1, 0]}
        />
      ) : (
        <FlyCamera />
      )}

      {/* Fog for atmosphere on realistic terrain */}
      {isRealisticScale && (
        <fog attach="fog" args={['#b0c4de', 1000, 15000]} />
      )}

      {/* HDRI Environment for lighting and skybox */}
      <Environment files="/autumn_hill_view_4k.hdr" background />
    </>
  );
}

export function SimulationCanvas() {
  const terrain = useSimulationStore((state) => state.terrain);

  // Adjust camera for large-scale terrain
  const isRealisticScale = terrain?.coordinateMapping?.metersPerUnit === 1;

  // Get terrain center Y for positioning camera
  const terrainYCenter = terrain?.mesh?.boundsMin && terrain?.mesh?.boundsMax
    ? (terrain.mesh.boundsMin[1] + terrain.mesh.boundsMax[1]) / 2
    : 0;
  const terrainHeight = terrain?.mesh?.boundsMin && terrain?.mesh?.boundsMax
    ? terrain.mesh.boundsMax[1] - terrain.mesh.boundsMin[1]
    : 0;

  // Position camera based on terrain scale and elevation
  // Start near origin at drone level for close-up view
  const cameraPosition: [number, number, number] = isRealisticScale
    ? [
        20,                     // Close to origin X
        terrainYCenter + 15,    // Slightly above terrain center (drone hover height)
        20                      // Close to origin Z
      ]
    : [8, 8, 8];

  console.log('[SimulationCanvas] Camera setup:', {
    isRealisticScale,
    terrainYCenter,
    terrainHeight,
    cameraPosition,
    terrainBounds: terrain?.mesh ? {
      min: terrain.mesh.boundsMin,
      max: terrain.mesh.boundsMax
    } : null
  });

  return (
    <Canvas
      camera={{
        position: cameraPosition,
        fov: 60,
        near: isRealisticScale ? 1 : 0.1,
        far: isRealisticScale ? 20000 : 1000,  // 20km far plane for 1km terrain
      }}
      gl={{ antialias: true, alpha: false, logarithmicDepthBuffer: true }}
      dpr={[1, 2]}
      shadows
    >
      <Scene />
      {import.meta.env.DEV && <Stats />}
    </Canvas>
  );
}

/**
 * Camera mode toggle button
 */
export function CameraModeToggle() {
  const { cameraMode, setCameraMode } = useSimulationStore();

  return (
    <button
      onClick={() => setCameraMode(cameraMode === 'fly' ? 'orbit' : 'fly')}
      style={{
        position: 'absolute',
        top: '10px',
        right: '60px',
        background: cameraMode === 'fly' ? 'rgba(100, 150, 255, 0.3)' : 'rgba(255, 255, 255, 0.1)',
        border: '1px solid rgba(255, 255, 255, 0.3)',
        borderRadius: '6px',
        padding: '8px 12px',
        color: 'white',
        cursor: 'pointer',
        fontSize: '12px',
        fontFamily: 'system-ui, sans-serif',
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
      }}
      title={cameraMode === 'fly' ? 'Switch to Orbit mode' : 'Switch to Fly mode'}
    >
      <span>{cameraMode === 'fly' ? '🎮' : '🔄'}</span>
      <span>{cameraMode === 'fly' ? 'Fly' : 'Orbit'}</span>
    </button>
  );
}

// Re-export FlyCameraHUD
export { FlyCameraHUD } from './FlyCamera';
