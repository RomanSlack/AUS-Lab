import { useRef, useMemo, useEffect, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import type { DroneState } from '../types/simulation';
import { useSimulationStore } from '../store/simulationStore';

interface DroneSwarmProps {
  drones: DroneState[];
  maxCount?: number;
}

// Scale factor - model is ~0.02 scale, we want ~0.2m drones, so 10x
const MODEL_SCALE = 10;

export function DroneSwarm({ drones, maxCount = 5000 }: DroneSwarmProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const selectedMeshRef = useRef<THREE.Mesh>(null);
  const outlineMeshRef = useRef<THREE.Mesh>(null);
  const [modelGeometry, setModelGeometry] = useState<THREE.BufferGeometry | null>(null);
  const { selectedDroneId } = useSimulationStore();

  // Load the GLB model
  const { scene } = useGLTF('/models/drone.glb');

  // Extract and merge ALL geometries from the model
  useEffect(() => {
    if (scene && !modelGeometry) {
      const geometries: THREE.BufferGeometry[] = [];

      scene.traverse((child) => {
        if (child instanceof THREE.Mesh && child.geometry) {
          const geo = child.geometry.clone();

          // Apply the mesh's world transform to the geometry
          child.updateWorldMatrix(true, false);
          geo.applyMatrix4(child.matrixWorld);

          geometries.push(geo);
        }
      });

      if (geometries.length > 0) {
        // Merge all geometries into one
        const merged = geometries.length === 1
          ? geometries[0]
          : mergeGeometries(geometries);

        if (merged) {
          // Scale the geometry
          merged.scale(MODEL_SCALE, MODEL_SCALE, MODEL_SCALE);

          // Center it
          merged.computeBoundingBox();
          merged.center();

          setModelGeometry(merged);
          console.log('[DroneSwarm] Merged', geometries.length, 'geometries into drone model');
        }
      }
    }
  }, [scene, modelGeometry]);

  // Pre-allocate reusable objects
  const temp = useMemo(() => new THREE.Object3D(), []);
  const tempColor = useMemo(() => new THREE.Color(), []);

  // Fallback geometry while model loads
  const fallbackGeometry = useMemo(() => {
    return new THREE.BoxGeometry(0.2, 0.05, 0.2);
  }, []);

  // Use loaded geometry or fallback
  const geometry = modelGeometry || fallbackGeometry;

  // Material - grey drone color
  const material = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#666666',
        metalness: 0.5,
        roughness: 0.4,
      }),
    []
  );

  // Selected drone highlight material - yellow emissive
  const selectedMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#f5c518',
        emissive: '#f5c518',
        emissiveIntensity: 0.3,
        metalness: 0.6,
        roughness: 0.3,
      }),
    []
  );

  // Outline material - wireframe
  const outlineMaterial = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        color: '#f5c518',
        wireframe: true,
        transparent: true,
        opacity: 0.6,
      }),
    []
  );

  useFrame(() => {
    if (!meshRef.current) return;
    if (drones.length === 0) return;

    const selectedDrone = selectedDroneId !== null
      ? drones.find(d => d.id === selectedDroneId)
      : null;

    drones.forEach((drone, i) => {
      // Convert PyBullet coordinates to Three.js
      // PyBullet: X-right, Y-forward, Z-up
      // Three.js: X-right, Y-up, Z-forward (towards camera)
      temp.position.set(
        drone.pos[0],
        drone.pos[2],
        -drone.pos[1]
      );

      // Apply yaw rotation around Y axis
      temp.rotation.set(0, -drone.yaw, 0);

      temp.updateMatrix();
      meshRef.current!.setMatrixAt(i, temp.matrix);

      // Dim selected drone in instanced mesh (it will be rendered separately)
      if (drone.id === selectedDroneId) {
        tempColor.setRGB(0.2, 0.2, 0.2); // Dim it
      } else {
        tempColor.setRGB(1, 1, 1); // Normal
      }
      meshRef.current!.setColorAt(i, tempColor);
    });

    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true;
    }
    meshRef.current.count = drones.length;

    // Update selected drone mesh position
    if (selectedMeshRef.current && outlineMeshRef.current && selectedDrone) {
      selectedMeshRef.current.position.set(
        selectedDrone.pos[0],
        selectedDrone.pos[2],
        -selectedDrone.pos[1]
      );
      selectedMeshRef.current.rotation.set(0, -selectedDrone.yaw, 0);
      selectedMeshRef.current.visible = true;

      // Outline slightly larger
      outlineMeshRef.current.position.copy(selectedMeshRef.current.position);
      outlineMeshRef.current.rotation.copy(selectedMeshRef.current.rotation);
      outlineMeshRef.current.scale.setScalar(1.15);
      outlineMeshRef.current.visible = true;
    } else if (selectedMeshRef.current && outlineMeshRef.current) {
      selectedMeshRef.current.visible = false;
      outlineMeshRef.current.visible = false;
    }
  });

  // Key to force re-create when geometry changes
  const geoKey = modelGeometry ? 'model' : 'fallback';

  return (
    <>
      {/* Main instanced mesh for all drones */}
      <instancedMesh
        key={geoKey}
        ref={meshRef}
        args={[geometry, material, maxCount]}
        frustumCulled={false}
        castShadow
        receiveShadow
      />

      {/* Selected drone highlight mesh */}
      <mesh
        ref={selectedMeshRef}
        geometry={geometry}
        material={selectedMaterial}
        visible={false}
        castShadow
      />

      {/* Selected drone outline mesh */}
      <mesh
        ref={outlineMeshRef}
        geometry={geometry}
        material={outlineMaterial}
        visible={false}
      />
    </>
  );
}

useGLTF.preload('/models/drone.glb');
