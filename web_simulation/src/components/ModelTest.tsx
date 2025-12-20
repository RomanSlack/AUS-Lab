import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Environment, Grid } from '@react-three/drei';
import { Suspense } from 'react';

function DroneModel() {
  const { scene } = useGLTF('/models/drone.glb');

  console.log('[ModelTest] Loaded scene:', scene);
  console.log('[ModelTest] Children:', scene.children.length);

  // Log all meshes found
  scene.traverse((child) => {
    if ((child as any).isMesh) {
      console.log('[ModelTest] Mesh:', child.name, 'geometry:', (child as any).geometry);
    }
  });

  // Center the model by resetting child positions
  scene.traverse((child) => {
    if (child.position) {
      child.position.set(0, 0, 0);
    }
  });

  // Model is very small (scale ~0.02), so we need to scale it up ~50x
  return (
    <primitive
      object={scene}
      scale={50}
      position={[0, 0, 0]}
    />
  );
}

function TestScene() {
  return (
    <>
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={1} />
      <pointLight position={[-10, -10, -5]} intensity={0.5} />

      <Suspense fallback={<mesh><boxGeometry /><meshStandardMaterial color="red" /></mesh>}>
        <DroneModel />
      </Suspense>

      <Grid args={[10, 10]} position={[0, -0.5, 0]} />
      <OrbitControls />
      <Environment preset="city" />
    </>
  );
}

export function ModelTest() {
  return (
    <div style={{ width: '100vw', height: '100vh', background: '#1a1a2e' }}>
      <div style={{
        position: 'absolute',
        top: 10,
        left: 10,
        color: 'white',
        zIndex: 100,
        background: 'rgba(0,0,0,0.7)',
        padding: '10px',
        borderRadius: '5px'
      }}>
        <h2>Model Test Page</h2>
        <p>Check console for model info</p>
        <p>Use mouse to orbit around</p>
      </div>
      <Canvas camera={{ position: [3, 3, 3], fov: 50 }}>
        <color attach="background" args={['#1a1a2e']} />
        <TestScene />
      </Canvas>
    </div>
  );
}

useGLTF.preload('/models/drone.glb');
