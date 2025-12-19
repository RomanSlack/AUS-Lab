import { useCallback } from 'react';
import { useSimulationStore } from '../store/simulationStore';
import type { FormationPattern } from '../types/simulation';

export function useCommands() {
  const { ws } = useSimulationStore();

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

  return {
    takeoff: (ids: number[] | ['all'] = ['all'], altitude: number = 1.5) =>
      sendCommand('takeoff', { ids, altitude }),

    land: (ids: number[] | ['all'] = ['all']) =>
      sendCommand('land', { ids }),

    hover: (ids: number[] | ['all'] = ['all']) =>
      sendCommand('hover', { ids }),

    goto: (id: number, x: number, y: number, z: number, yaw: number = 0) =>
      sendCommand('goto', { id, x, y, z, yaw }),

    velocity: (id: number, vx: number, vy: number, vz: number, yaw_rate: number = 0) =>
      sendCommand('velocity', { id, vx, vy, vz, yaw_rate }),

    formation: (
      pattern: FormationPattern,
      center: [number, number, number] = [0, 0, 1.5],
      options: { spacing?: number; radius?: number; axis?: 'x' | 'y' } = {}
    ) =>
      sendCommand('formation', { pattern, center, ...options }),

    spawn: (num: number = 5) =>
      sendCommand('spawn', { num }),

    reset: () =>
      sendCommand('reset', {}),

    setSpeed: (speed: number) =>
      sendCommand('speed', { speed }),
  };
}
