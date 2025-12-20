import { useRef } from 'react';
import { Canvas, ThreeEvent } from '@react-three/fiber';
import { OrbitControls, Grid, Environment, Stats } from '@react-three/drei';
import * as THREE from 'three';
import { DroneSwarm } from './DroneSwarm';
import { useSimulationStore } from '../store/simulationStore';
import { useCommands } from '../hooks/useCommands';

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

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    if (event.point) {
      onGroundClick(event.point);
    }
  };

  return (
    <mesh
      ref={meshRef}
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, 0, 0]}
      receiveShadow
      onClick={handleClick}
    >
      <planeGeometry args={[50, 50]} />
      <meshStandardMaterial color="#2a4a2a" roughness={0.9} metalness={0.1} />
    </mesh>
  );
}

function Scene() {
  const { drones, waypoint, setWaypoint, monitorMode } = useSimulationStore();
  const { waypoint: sendWaypoint, monitor: sendMonitor } = useCommands();

  const handleGroundClick = (point: THREE.Vector3) => {
    // Convert Three.js coords (x, y, z) to PyBullet (x, -z, y)
    // Three.js: x-right, y-up, z-towards camera
    // PyBullet: x-right, y-forward, z-up
    const pybulletX = point.x;
    const pybulletY = -point.z;
    const pybulletZ = 1.5; // Default hover altitude

    setWaypoint([pybulletX, pybulletY, pybulletZ]);

    if (monitorMode) {
      console.log(`[Monitor] Surveillance mode at (${pybulletX.toFixed(2)}, ${pybulletY.toFixed(2)}, ${pybulletZ.toFixed(2)})`);
      sendMonitor(pybulletX, pybulletY, pybulletZ);
    } else {
      console.log(`[Waypoint] Go to (${pybulletX.toFixed(2)}, ${pybulletY.toFixed(2)}, ${pybulletZ.toFixed(2)})`);
      sendWaypoint(pybulletX, pybulletY, pybulletZ);
    }
  };

  return (
    <>
      {/* Additional lighting for shadows (HDRI provides main lighting) */}
      <directionalLight
        position={[10, 20, 10]}
        intensity={0.5}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-far={50}
        shadow-camera-left={-20}
        shadow-camera-right={20}
        shadow-camera-top={20}
        shadow-camera-bottom={-20}
      />

      {/* Clickable Ground */}
      <ClickableGround onGroundClick={handleGroundClick} />

      {/* Waypoint marker */}
      {waypoint && <WaypointMarker position={waypoint} isMonitor={monitorMode} />}

      {/* Grid */}
      <Grid
        position={[0, 0.01, 0]}
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

      {/* Drones */}
      <DroneSwarm drones={drones} />

      {/* Camera controls */}
      <OrbitControls
        enableDamping
        dampingFactor={0.05}
        minDistance={2}
        maxDistance={50}
        maxPolarAngle={Math.PI / 2.1}
        target={[0, 1, 0]}
      />

      {/* HDRI Environment for lighting and skybox */}
      <Environment files="/autumn_hill_view_4k.hdr" background />
    </>
  );
}

export function SimulationCanvas() {
  return (
    <Canvas
      camera={{ position: [8, 8, 8], fov: 60 }}
      gl={{ antialias: true, alpha: false }}
      dpr={[1, 2]}
      shadows
    >
      <Scene />
      {import.meta.env.DEV && <Stats />}
    </Canvas>
  );
}
