import { useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { useFBO } from '@react-three/drei';
import * as THREE from 'three';
import { useSimulationStore } from '../store/simulationStore';

// Resolution for FPV render (higher res for fullscreen support)
const FPV_WIDTH = 640;
const FPV_HEIGHT = 400;

// Throttle FPV updates to ~30fps for performance
const FPV_UPDATE_INTERVAL = 1 / 30;

export function DroneFPVCamera() {
  const selectedDroneId = useSimulationStore(state => state.selectedDroneId);
  const drones = useSimulationStore(state => state.drones);
  const setFpvTexture = useSimulationStore(state => state.setFpvTexture);
  const { gl, scene } = useThree();

  // Create FPV camera
  const fpvCamera = useRef(new THREE.PerspectiveCamera(90, FPV_WIDTH / FPV_HEIGHT, 0.1, 100));

  // Throttle timer
  const lastUpdateRef = useRef(0);

  // Reusable buffers to avoid GC pressure
  const pixelsRef = useRef(new Uint8Array(FPV_WIDTH * FPV_HEIGHT * 4));
  const flippedRef = useRef(new Uint8Array(FPV_WIDTH * FPV_HEIGHT * 4));

  // Create FBO (Frame Buffer Object) for off-screen rendering
  const fbo = useFBO(FPV_WIDTH, FPV_HEIGHT, {
    minFilter: THREE.LinearFilter,
    magFilter: THREE.LinearFilter,
    format: THREE.RGBAFormat,
    type: THREE.UnsignedByteType,
  });

  useFrame((_, delta) => {
    // Throttle updates
    lastUpdateRef.current += delta;
    if (lastUpdateRef.current < FPV_UPDATE_INTERVAL) {
      return;
    }
    lastUpdateRef.current = 0;

    // Get selected drone
    const selectedDrone = selectedDroneId !== null
      ? drones.find(d => d.id === selectedDroneId)
      : null;

    if (!selectedDrone) {
      return;
    }

    // Convert PyBullet coordinates to Three.js
    // PyBullet: X-right, Y-forward, Z-up
    // Three.js: X-right, Y-up, Z-forward (towards camera)
    const droneX = selectedDrone.pos[0];
    const droneY = selectedDrone.pos[2]; // Z becomes Y (up)
    const droneZ = -selectedDrone.pos[1]; // Y becomes -Z (forward)
    const droneYaw = -selectedDrone.yaw;

    // Position camera slightly above and behind the drone
    const cameraOffset = 0.15; // Height above drone center
    fpvCamera.current.position.set(droneX, droneY + cameraOffset, droneZ);

    // Look in the direction the drone is facing (forward is -Z in Three.js when yaw=0)
    const lookDistance = 10;
    const lookX = droneX + Math.sin(droneYaw) * lookDistance;
    const lookZ = droneZ - Math.cos(droneYaw) * lookDistance;
    fpvCamera.current.lookAt(lookX, droneY, lookZ);

    // Render scene from FPV camera to FBO
    gl.setRenderTarget(fbo);
    gl.render(scene, fpvCamera.current);
    gl.setRenderTarget(null);

    // Read pixels into reusable buffer
    const pixels = pixelsRef.current;
    gl.readRenderTargetPixels(fbo, 0, 0, FPV_WIDTH, FPV_HEIGHT, pixels);

    // Flip vertically (WebGL renders upside down) into reusable buffer
    const flipped = flippedRef.current;
    for (let y = 0; y < FPV_HEIGHT; y++) {
      const srcRowStart = y * FPV_WIDTH * 4;
      const dstRowStart = (FPV_HEIGHT - 1 - y) * FPV_WIDTH * 4;
      for (let x = 0; x < FPV_WIDTH * 4; x++) {
        flipped[dstRowStart + x] = pixels[srcRowStart + x];
      }
    }

    // Create a copy for the store (store needs ownership)
    setFpvTexture(new Uint8Array(flipped));
  });

  return null; // This component doesn't render anything visible
}
