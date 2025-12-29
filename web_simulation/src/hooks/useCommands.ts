import { useCallback, useMemo } from 'react';
import { useSimulationStore } from '../store/simulationStore';
import type { FormationPattern } from '../types/simulation';

export function useCommands() {
  const ws = useSimulationStore(state => state.ws);

  const sendCommand = useCallback(
    (action: string, params: Record<string, unknown>) => {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.error('[Commands] WebSocket not connected');
        return false;
      }

      ws.send(
        JSON.stringify({
          type: 'command',
          payload: { action, params },
        })
      );
      return true;
    },
    [ws]
  );

  const takeoff = useCallback(
    (ids: number[] | ['all'] = ['all'], altitude: number = 1.5) =>
      sendCommand('takeoff', { ids, altitude }),
    [sendCommand]
  );

  const land = useCallback(
    (ids: number[] | ['all'] = ['all']) =>
      sendCommand('land', { ids }),
    [sendCommand]
  );

  const hover = useCallback(
    (ids: number[] | ['all'] = ['all']) =>
      sendCommand('hover', { ids }),
    [sendCommand]
  );

  const goto = useCallback(
    (id: number, x: number, y: number, z: number, yaw: number = 0) =>
      sendCommand('goto', { id, x, y, z, yaw }),
    [sendCommand]
  );

  const velocity = useCallback(
    (id: number, vx: number, vy: number, vz: number, yaw_rate: number = 0) =>
      sendCommand('velocity', { id, vx, vy, vz, yaw_rate }),
    [sendCommand]
  );

  const formation = useCallback(
    (
      pattern: FormationPattern,
      center: [number, number, number] = [0, 0, 1.5],
      options: { spacing?: number; radius?: number; axis?: 'x' | 'y' } = {}
    ) =>
      sendCommand('formation', { pattern, center, ...options }),
    [sendCommand]
  );

  const spawn = useCallback(
    (num: number = 5) =>
      sendCommand('spawn', { num }),
    [sendCommand]
  );

  const reset = useCallback(
    () => sendCommand('reset', {}),
    [sendCommand]
  );

  const setSpeed = useCallback(
    (speed: number) =>
      sendCommand('speed', { speed }),
    [sendCommand]
  );

  const waypoint = useCallback(
    (x: number, y: number, z: number) =>
      sendCommand('waypoint', { x, y, z }),
    [sendCommand]
  );

  const monitor = useCallback(
    (x: number, y: number, z: number) =>
      sendCommand('monitor', { x, y, z }),
    [sendCommand]
  );

  return useMemo(() => ({
    takeoff,
    land,
    hover,
    goto,
    velocity,
    formation,
    spawn,
    reset,
    setSpeed,
    waypoint,
    monitor,
  }), [takeoff, land, hover, goto, velocity, formation, spawn, reset, setSpeed, waypoint, monitor]);
}
