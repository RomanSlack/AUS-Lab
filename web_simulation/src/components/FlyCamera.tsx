import { useRef, useEffect, useCallback } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useSimulationStore } from '../store/simulationStore';

/**
 * Fly camera controller - WASD movement with mouse look.
 * Similar to Unity/Unreal/Blender fly mode.
 *
 * Controls:
 * - WASD: Move forward/left/back/right
 * - Space: Move up
 * - Shift: Move down
 * - Mouse: Look around (when pointer locked)
 * - Scroll: Adjust speed
 * - Right-click: Enter fly mode (pointer lock)
 * - Escape: Exit fly mode
 */
export function FlyCamera() {
  const { camera, gl } = useThree();
  const { cameraMode, flySpeed, setFlySpeed } = useSimulationStore();

  // Movement state
  const moveState = useRef({
    forward: false,
    backward: false,
    left: false,
    right: false,
    up: false,
    down: false,
  });

  // Mouse state
  const isLocked = useRef(false);
  const euler = useRef(new THREE.Euler(0, 0, 0, 'YXZ'));

  // Handle keyboard
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (cameraMode !== 'fly') return;

    switch (e.code) {
      case 'KeyW':
        moveState.current.forward = true;
        break;
      case 'KeyS':
        moveState.current.backward = true;
        break;
      case 'KeyA':
        moveState.current.left = true;
        break;
      case 'KeyD':
        moveState.current.right = true;
        break;
      case 'Space':
        moveState.current.up = true;
        e.preventDefault();
        break;
      case 'ShiftLeft':
      case 'ShiftRight':
        moveState.current.down = true;
        break;
    }
  }, [cameraMode]);

  const handleKeyUp = useCallback((e: KeyboardEvent) => {
    switch (e.code) {
      case 'KeyW':
        moveState.current.forward = false;
        break;
      case 'KeyS':
        moveState.current.backward = false;
        break;
      case 'KeyA':
        moveState.current.left = false;
        break;
      case 'KeyD':
        moveState.current.right = false;
        break;
      case 'Space':
        moveState.current.up = false;
        break;
      case 'ShiftLeft':
      case 'ShiftRight':
        moveState.current.down = false;
        break;
    }
  }, []);

  // Handle mouse movement
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isLocked.current || cameraMode !== 'fly') return;

    const sensitivity = 0.002;
    euler.current.setFromQuaternion(camera.quaternion);
    euler.current.y -= e.movementX * sensitivity;
    euler.current.x -= e.movementY * sensitivity;

    // Clamp vertical rotation
    euler.current.x = Math.max(-Math.PI / 2 + 0.01, Math.min(Math.PI / 2 - 0.01, euler.current.x));

    camera.quaternion.setFromEuler(euler.current);
  }, [camera, cameraMode]);

  // Handle scroll for speed
  const handleWheel = useCallback((e: WheelEvent) => {
    if (cameraMode !== 'fly') return;

    const delta = e.deltaY > 0 ? 0.8 : 1.25;
    const newSpeed = Math.max(5, Math.min(500, flySpeed * delta));
    setFlySpeed(newSpeed);
  }, [cameraMode, flySpeed, setFlySpeed]);

  // Handle pointer lock
  const handleClick = useCallback((e: MouseEvent) => {
    if (cameraMode !== 'fly') return;

    // Right-click to enter fly mode
    if (e.button === 2) {
      e.preventDefault();
      gl.domElement.requestPointerLock();
    }
  }, [cameraMode, gl.domElement]);

  const handlePointerLockChange = useCallback(() => {
    isLocked.current = document.pointerLockElement === gl.domElement;
  }, [gl.domElement]);

  // Prevent context menu
  const handleContextMenu = useCallback((e: Event) => {
    if (cameraMode === 'fly') {
      e.preventDefault();
    }
  }, [cameraMode]);

  // Set up event listeners
  useEffect(() => {
    const canvas = gl.domElement;

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    document.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('wheel', handleWheel, { passive: true });
    canvas.addEventListener('mousedown', handleClick);
    canvas.addEventListener('contextmenu', handleContextMenu);
    document.addEventListener('pointerlockchange', handlePointerLockChange);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      document.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('wheel', handleWheel);
      canvas.removeEventListener('mousedown', handleClick);
      canvas.removeEventListener('contextmenu', handleContextMenu);
      document.removeEventListener('pointerlockchange', handlePointerLockChange);
    };
  }, [gl.domElement, handleKeyDown, handleKeyUp, handleMouseMove, handleWheel, handleClick, handleContextMenu, handlePointerLockChange]);

  // Update camera position each frame
  useFrame((_, delta) => {
    if (cameraMode !== 'fly') return;

    const speed = flySpeed * delta;
    const direction = new THREE.Vector3();

    // Get forward/right vectors from camera
    const forward = new THREE.Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
    const right = new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion);

    // Apply movement
    if (moveState.current.forward) direction.add(forward);
    if (moveState.current.backward) direction.sub(forward);
    if (moveState.current.right) direction.add(right);
    if (moveState.current.left) direction.sub(right);
    if (moveState.current.up) direction.y += 1;
    if (moveState.current.down) direction.y -= 1;

    if (direction.length() > 0) {
      direction.normalize().multiplyScalar(speed);
      camera.position.add(direction);
    }
  });

  return null; // This component doesn't render anything
}

/**
 * UI overlay showing fly camera controls
 */
export function FlyCameraHUD() {
  const { cameraMode, flySpeed } = useSimulationStore();

  if (cameraMode !== 'fly') return null;

  return (
    <div style={{
      position: 'absolute',
      bottom: '80px',
      left: '10px',
      background: 'rgba(0, 0, 0, 0.7)',
      color: 'white',
      padding: '8px 12px',
      borderRadius: '6px',
      fontSize: '11px',
      fontFamily: 'monospace',
      pointerEvents: 'none',
      zIndex: 100,
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>Fly Mode</div>
      <div>Right-click: Look around</div>
      <div>WASD: Move | Space/Shift: Up/Down</div>
      <div>Scroll: Speed ({flySpeed.toFixed(0)} m/s)</div>
    </div>
  );
}
