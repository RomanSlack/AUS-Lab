import { useEffect, useRef, useCallback } from 'react';
import { useSimulationStore } from '../store/simulationStore';
import type { ServerMessage } from '../types/simulation';

const WS_URL = 'ws://localhost:8000/ws';
const RECONNECT_DELAY = 2000;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number>();

  const { setConnected, updateState, setWs } = useSimulationStore();

  const connect = useCallback(() => {
    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    console.log('[WebSocket] Connecting to', WS_URL);
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WebSocket] Connected');
      setConnected(true);
      setWs(ws);
    };

    ws.onmessage = (event) => {
      try {
        const message: ServerMessage = JSON.parse(event.data);

        if (message.type === 'state') {
          updateState(message.payload.drones, message.payload.timestamp);
        } else if (message.type === 'ack') {
          console.log('[WebSocket] Command ack:', message.payload.message);
        }
      } catch (e) {
        console.error('[WebSocket] Parse error:', e);
      }
    };

    ws.onclose = () => {
      console.log('[WebSocket] Disconnected, reconnecting in', RECONNECT_DELAY, 'ms');
      setConnected(false);
      setWs(null);

      // Schedule reconnect
      reconnectTimeoutRef.current = window.setTimeout(connect, RECONNECT_DELAY);
    };

    ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
      ws.close();
    };
  }, [setConnected, updateState, setWs]);

  useEffect(() => {
    connect();

    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);
}
