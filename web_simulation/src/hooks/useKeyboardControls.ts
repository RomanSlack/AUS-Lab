import { useEffect, useRef } from 'react';
import { useSimulationStore, KeyboardState } from '../store/simulationStore';
import { useCommands } from './useCommands';

const KEY_MAP: Record<string, keyof KeyboardState> = {
  w: 'w',
  W: 'w',
  a: 'a',
  A: 'a',
  s: 's',
  S: 's',
  d: 'd',
  D: 'd',
  ' ': 'space',
  Shift: 'shift',
  q: 'q',
  Q: 'q',
  e: 'e',
  E: 'e',
};

// Velocity settings
const HORIZONTAL_SPEED = 1.5; // m/s
const VERTICAL_SPEED = 1.0; // m/s
const YAW_RATE = 1.0; // rad/s

export function useKeyboardControls() {
  const selectedDroneId = useSimulationStore(state => state.selectedDroneId);
  const setKey = useSimulationStore(state => state.setKey);
  const setManualControlActive = useSimulationStore(state => state.setManualControlActive);
  const { velocity, hover } = useCommands();

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wasMovingRef = useRef(false);
  const selectedDroneIdRef = useRef(selectedDroneId);

  // Keep ref in sync
  useEffect(() => {
    selectedDroneIdRef.current = selectedDroneId;
  }, [selectedDroneId]);

  // Handle key events
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture if typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      const key = KEY_MAP[e.key];
      if (key && selectedDroneIdRef.current !== null) {
        e.preventDefault();
        setKey(key, true);
        setManualControlActive(true);
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const key = KEY_MAP[e.key];
      if (key) {
        setKey(key, false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [setKey, setManualControlActive]);

  // Send velocity commands while keys are pressed
  useEffect(() => {
    if (selectedDroneId === null) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    const sendVelocityCommand = () => {
      const droneId = selectedDroneIdRef.current;
      if (droneId === null) return;

      // Get current keys state directly from store
      const keys = useSimulationStore.getState().keys;

      // Calculate velocity based on pressed keys
      let vx = 0;
      let vy = 0;
      let vz = 0;
      let yawRate = 0;

      // W/S - Forward/Backward (PyBullet Y axis)
      if (keys.w) vy += HORIZONTAL_SPEED;
      if (keys.s) vy -= HORIZONTAL_SPEED;

      // A/D - Left/Right (PyBullet X axis)
      if (keys.a) vx -= HORIZONTAL_SPEED;
      if (keys.d) vx += HORIZONTAL_SPEED;

      // Space/Shift - Up/Down (PyBullet Z axis)
      if (keys.space) vz += VERTICAL_SPEED;
      if (keys.shift) vz -= VERTICAL_SPEED;

      // Q/E - Yaw rotation
      if (keys.q) yawRate += YAW_RATE;
      if (keys.e) yawRate -= YAW_RATE;

      const isMoving = vx !== 0 || vy !== 0 || vz !== 0 || yawRate !== 0;

      if (isMoving) {
        // Send velocity command
        velocity(droneId, vx, vy, vz, yawRate);
        wasMovingRef.current = true;
      } else if (wasMovingRef.current) {
        // All keys released - send hover to stop the drone
        hover([droneId]);
        wasMovingRef.current = false;
        setManualControlActive(false);
      }
    };

    // Send commands at 20Hz
    intervalRef.current = setInterval(sendVelocityCommand, 50);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [selectedDroneId, velocity, hover, setManualControlActive]);

  return useSimulationStore(state => state.keys);
}
