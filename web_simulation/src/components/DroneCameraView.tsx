import { useRef, useEffect, useState } from 'react';
import { useSimulationStore } from '../store/simulationStore';

// Match resolution with DroneFPVCamera
const FPV_WIDTH = 640;
const FPV_HEIGHT = 400;

export function DroneCameraView() {
  const { selectedDroneId, drones, fpvTexture } = useSimulationStore();
  const selectedDrone = drones.find((d) => d.id === selectedDroneId);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Draw FPV camera feed or synthetic view
  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = FPV_WIDTH;
    canvas.height = FPV_HEIGHT;

    if (fpvTexture && selectedDrone) {
      // Draw the FPV texture from the 3D renderer
      const imageData = ctx.createImageData(FPV_WIDTH, FPV_HEIGHT);
      imageData.data.set(fpvTexture);
      ctx.putImageData(imageData, 0, 0);

      // Draw HUD overlay on top of FPV feed
      drawHUDOverlay(ctx, canvas, selectedDrone);
    } else if (selectedDrone) {
      // Fallback: Draw synthetic camera view
      drawSyntheticView(ctx, canvas, selectedDrone);
    } else {
      // No drone selected - clear to black
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
  }, [selectedDrone, fpvTexture]);

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  if (selectedDroneId === null) {
    return (
      <div className="drone-camera-view" ref={containerRef}>
        <div className="no-drone-selected">
          <span>No drone selected</span>
          <span style={{ fontSize: '0.6rem', marginTop: '4px', opacity: 0.6 }}>
            Click a drone in the HUD
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`drone-camera-view ${isFullscreen ? 'fullscreen' : ''}`}
      ref={containerRef}
    >
      <div className="camera-header">
        <span className="camera-title">Drone {selectedDroneId} - FPV</span>
        <div className="camera-controls">
          <button className="camera-fullscreen-btn" onClick={toggleFullscreen}>
            {isFullscreen ? 'Exit' : 'Expand'}
          </button>
          <div className="camera-rec">
            <div className="camera-rec-dot" />
            <span>Live</span>
          </div>
        </div>
      </div>

      <canvas ref={canvasRef} className="camera-canvas" />

      <div className="camera-crosshair">
        <div className="crosshair-h" />
        <div className="crosshair-v" />
      </div>

      {selectedDrone && (
        <div className="camera-overlay">
          <div className="camera-telemetry">
            <div className="telemetry-item">
              <span className="telemetry-label">POS</span>
              {selectedDrone.pos[0].toFixed(1)}, {selectedDrone.pos[1].toFixed(1)}
            </div>
            <div className="telemetry-item">
              <span className="telemetry-label">BAT</span>
              {selectedDrone.battery.toFixed(0)}%
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Draw HUD overlay on top of FPV feed
function drawHUDOverlay(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, drone: { yaw: number; pos: number[]; vel: number[] }) {
  // Semi-transparent heading indicator at top
  const heading = ((drone.yaw * 180) / Math.PI + 360) % 360;
  ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
  ctx.fillRect(canvas.width / 2 - 30, 5, 60, 20);
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
  ctx.strokeRect(canvas.width / 2 - 30, 5, 60, 20);
  ctx.fillStyle = '#fff';
  ctx.font = '12px monospace';
  ctx.textAlign = 'center';
  ctx.fillText(`${heading.toFixed(0)}°`, canvas.width / 2, 18);

  // Altitude indicator on right
  ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
  ctx.fillRect(canvas.width - 50, canvas.height / 2 - 15, 45, 30);
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
  ctx.strokeRect(canvas.width - 50, canvas.height / 2 - 15, 45, 30);
  ctx.fillStyle = '#22c55e';
  ctx.font = '10px monospace';
  ctx.textAlign = 'right';
  ctx.fillText('ALT', canvas.width - 10, canvas.height / 2 - 3);
  ctx.fillStyle = '#fff';
  ctx.font = '11px monospace';
  ctx.fillText(`${drone.pos[2].toFixed(1)}m`, canvas.width - 10, canvas.height / 2 + 10);

  // Speed indicator on left
  const speed = Math.sqrt(drone.vel[0] ** 2 + drone.vel[1] ** 2 + drone.vel[2] ** 2);
  ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
  ctx.fillRect(5, canvas.height / 2 - 15, 45, 30);
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
  ctx.strokeRect(5, canvas.height / 2 - 15, 45, 30);
  ctx.fillStyle = '#22c55e';
  ctx.font = '10px monospace';
  ctx.textAlign = 'left';
  ctx.fillText('SPD', 10, canvas.height / 2 - 3);
  ctx.fillStyle = '#fff';
  ctx.font = '11px monospace';
  ctx.fillText(`${speed.toFixed(1)}`, 10, canvas.height / 2 + 10);

  // Crosshair
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
  ctx.lineWidth = 1;
  const cx = canvas.width / 2;
  const cy = canvas.height / 2;
  // Horizontal
  ctx.beginPath();
  ctx.moveTo(cx - 20, cy);
  ctx.lineTo(cx - 8, cy);
  ctx.moveTo(cx + 8, cy);
  ctx.lineTo(cx + 20, cy);
  ctx.stroke();
  // Vertical
  ctx.beginPath();
  ctx.moveTo(cx, cy - 20);
  ctx.lineTo(cx, cy - 8);
  ctx.moveTo(cx, cy + 8);
  ctx.lineTo(cx, cy + 20);
  ctx.stroke();
}

// Fallback synthetic view when FPV texture isn't available
function drawSyntheticView(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, drone: { yaw: number; pos: number[]; vel: number[] }) {
  // Clear
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const horizonY = canvas.height / 2;

  // Draw sky gradient
  const skyGradient = ctx.createLinearGradient(0, 0, 0, horizonY);
  skyGradient.addColorStop(0, '#1a1a2e');
  skyGradient.addColorStop(1, '#2d3748');
  ctx.fillStyle = skyGradient;
  ctx.fillRect(0, 0, canvas.width, horizonY);

  // Draw ground gradient
  const groundGradient = ctx.createLinearGradient(0, horizonY, 0, canvas.height);
  groundGradient.addColorStop(0, '#2d4a2d');
  groundGradient.addColorStop(1, '#1a2e1a');
  ctx.fillStyle = groundGradient;
  ctx.fillRect(0, horizonY, canvas.width, canvas.height - horizonY);

  // Draw horizon line
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, horizonY);
  ctx.lineTo(canvas.width, horizonY);
  ctx.stroke();

  // Draw grid lines on ground
  ctx.strokeStyle = 'rgba(100, 100, 100, 0.3)';
  for (let i = 1; i <= 8; i++) {
    const y = horizonY + (i * i * 2);
    if (y > canvas.height) break;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }

  const vanishX = canvas.width / 2;
  for (let i = -4; i <= 4; i++) {
    const bottomX = vanishX + i * 40;
    ctx.beginPath();
    ctx.moveTo(vanishX, horizonY);
    ctx.lineTo(bottomX, canvas.height);
    ctx.stroke();
  }

  // "NO SIGNAL" text
  ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
  ctx.font = '14px monospace';
  ctx.textAlign = 'center';
  ctx.fillText('SYNTHETIC VIEW', canvas.width / 2, 40);

  // Draw HUD overlay
  drawHUDOverlay(ctx, canvas, drone);
}
