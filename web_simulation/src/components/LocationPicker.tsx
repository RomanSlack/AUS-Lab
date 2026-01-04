import { useState, useCallback } from 'react';
import { useSimulationStore } from '../store/simulationStore';
import { TERRAIN_PRESETS, type TerrainLoadResponse, type TerrainPreset } from '../types/simulation';

const API_URL = 'http://localhost:8000';

type Resolution = 'low' | 'medium' | 'high' | 'ultra';

interface LocationPickerProps {
  onClose?: () => void;
}

/**
 * Component for selecting and loading real-world terrain.
 *
 * Features:
 * - Preset locations (Lake Tahoe, Grand Canyon, etc.)
 * - Custom lat/lng input
 * - Adjustable area size
 * - Realistic 1:1 scale option
 * - Resolution quality selector
 */
export function LocationPicker({ onClose }: LocationPickerProps) {
  const { setTerrain, setTerrainLoading, setTerrainError, terrainLoading, terrainError, clearTerrain } = useSimulationStore();

  const [selectedPreset, setSelectedPreset] = useState<TerrainPreset | null>(null);
  const [customLat, setCustomLat] = useState('39.0968');
  const [customLng, setCustomLng] = useState('-120.0324');
  const [areaSize, setAreaSize] = useState(2000);
  const [useCustom, setUseCustom] = useState(false);
  const [realisticScale, setRealisticScale] = useState(true); // Default to realistic
  const [resolution, setResolution] = useState<Resolution>('high');

  const loadTerrain = useCallback(async () => {
    const lat = useCustom ? parseFloat(customLat) : selectedPreset?.lat ?? 39.0968;
    const lng = useCustom ? parseFloat(customLng) : selectedPreset?.lng ?? -120.0324;
    const size = useCustom ? areaSize : selectedPreset?.sizeMeters ?? 2000;

    if (isNaN(lat) || isNaN(lng)) {
      setTerrainError('Invalid coordinates');
      return;
    }

    setTerrainLoading(true);
    setTerrainError(null);

    try {
      const response = await fetch(`${API_URL}/terrain/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat,
          lng,
          size_meters: size,
          realistic_scale: realisticScale,
          resolution: resolution,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to load terrain');
      }

      const data: TerrainLoadResponse = await response.json();
      setTerrain(data);
      onClose?.();
    } catch (err) {
      setTerrainError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setTerrainLoading(false);
    }
  }, [useCustom, customLat, customLng, areaSize, selectedPreset, realisticScale, resolution, setTerrain, setTerrainLoading, setTerrainError, onClose]);

  const handlePresetClick = (preset: TerrainPreset) => {
    setSelectedPreset(preset);
    setUseCustom(false);
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>Load Terrain</h3>
        {onClose && (
          <button onClick={onClose} style={styles.closeButton}>
            x
          </button>
        )}
      </div>

      {/* Presets */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Preset Locations</div>
        <div style={styles.presetGrid}>
          {TERRAIN_PRESETS.map((preset) => (
            <button
              key={preset.name}
              onClick={() => handlePresetClick(preset)}
              style={{
                ...styles.presetButton,
                ...(selectedPreset?.name === preset.name && !useCustom ? styles.presetButtonSelected : {}),
              }}
            >
              <div style={styles.presetName}>{preset.name}</div>
              <div style={styles.presetDesc}>{preset.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Custom coordinates */}
      <div style={styles.section}>
        <label style={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={useCustom}
            onChange={(e) => setUseCustom(e.target.checked)}
            style={styles.checkbox}
          />
          Use custom coordinates
        </label>

        {useCustom && (
          <div style={styles.customInputs}>
            <div style={styles.inputRow}>
              <label style={styles.inputLabel}>
                Latitude:
                <input
                  type="text"
                  value={customLat}
                  onChange={(e) => setCustomLat(e.target.value)}
                  style={styles.input}
                  placeholder="-90 to 90"
                />
              </label>
              <label style={styles.inputLabel}>
                Longitude:
                <input
                  type="text"
                  value={customLng}
                  onChange={(e) => setCustomLng(e.target.value)}
                  style={styles.input}
                  placeholder="-180 to 180"
                />
              </label>
            </div>
            <div style={styles.inputRow}>
              <label style={styles.inputLabel}>
                Area Size (meters):
                <input
                  type="range"
                  min={500}
                  max={10000}
                  step={500}
                  value={areaSize}
                  onChange={(e) => setAreaSize(parseInt(e.target.value))}
                  style={styles.slider}
                />
                <span style={styles.sliderValue}>{areaSize}m</span>
              </label>
            </div>
          </div>
        )}
      </div>

      {/* Scale and Resolution Options */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>Options</div>

        {/* Realistic Scale Toggle */}
        <label style={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={realisticScale}
            onChange={(e) => setRealisticScale(e.target.checked)}
            style={styles.checkbox}
          />
          <span>
            <strong>Realistic 1:1 Scale</strong>
            <span style={{ opacity: 0.6, marginLeft: '8px' }}>
              {realisticScale ? '(drones at actual size)' : '(scaled down 100x)'}
            </span>
          </span>
        </label>

        {/* Resolution Selector */}
        <div style={styles.resolutionRow}>
          <span style={styles.resolutionLabel}>Satellite Resolution:</span>
          <div style={styles.resolutionButtons}>
            {(['low', 'medium', 'high', 'ultra'] as Resolution[]).map((res) => (
              <button
                key={res}
                onClick={() => setResolution(res)}
                style={{
                  ...styles.resolutionButton,
                  ...(resolution === res ? styles.resolutionButtonSelected : {}),
                }}
              >
                {res.charAt(0).toUpperCase() + res.slice(1)}
              </button>
            ))}
          </div>
        </div>
        <div style={styles.resolutionHint}>
          {resolution === 'low' && '~4m per pixel (fastest)'}
          {resolution === 'medium' && '~2m per pixel (balanced)'}
          {resolution === 'high' && '~1m per pixel (detailed)'}
          {resolution === 'ultra' && '~0.5m per pixel (slow, best quality)'}
        </div>
      </div>

      {/* Selected location info */}
      {(selectedPreset || useCustom) && (
        <div style={styles.selectionInfo}>
          <strong>Selected:</strong>{' '}
          {useCustom
            ? `${customLat}, ${customLng} (${areaSize}m)`
            : `${selectedPreset?.name} (${selectedPreset?.sizeMeters}m)`}
          {realisticScale && <span style={{ color: '#88ff88' }}> - 1:1 Scale</span>}
        </div>
      )}

      {/* Error display */}
      {terrainError && (
        <div style={styles.error}>
          {terrainError}
        </div>
      )}

      {/* Actions */}
      <div style={styles.actions}>
        <button
          onClick={clearTerrain}
          style={styles.clearButton}
        >
          Clear Terrain
        </button>
        <button
          onClick={loadTerrain}
          disabled={terrainLoading || (!selectedPreset && !useCustom)}
          style={{
            ...styles.loadButton,
            ...(terrainLoading ? styles.loadButtonDisabled : {}),
          }}
        >
          {terrainLoading ? 'Loading...' : 'Load Terrain'}
        </button>
      </div>

      {/* Loading progress */}
      {terrainLoading && (
        <div style={styles.loadingOverlay}>
          <div style={styles.loadingSpinner} />
          <div style={styles.loadingText}>
            Fetching terrain tiles...
            <br />
            <span style={styles.loadingSubtext}>This may take a few seconds</span>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Compact button to toggle location picker
 */
export function TerrainToggleButton({ onClick }: { onClick: () => void }) {
  const terrain = useSimulationStore((state) => state.terrain);
  const terrainLoading = useSimulationStore((state) => state.terrainLoading);

  return (
    <button
      onClick={onClick}
      style={{
        ...styles.toggleButton,
        ...(terrain ? styles.toggleButtonActive : {}),
      }}
      title={terrain ? 'Change terrain' : 'Load terrain'}
    >
      {terrainLoading ? '...' : terrain ? '🏔️' : '🗺️'}
    </button>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    background: 'rgba(20, 20, 25, 0.95)',
    borderRadius: '12px',
    padding: '20px',
    minWidth: '400px',
    maxWidth: '500px',
    color: 'white',
    fontFamily: 'system-ui, sans-serif',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    zIndex: 1000,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
    paddingBottom: '12px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 600,
  },
  closeButton: {
    background: 'transparent',
    border: 'none',
    color: 'white',
    fontSize: '20px',
    cursor: 'pointer',
    padding: '4px 8px',
    opacity: 0.7,
  },
  section: {
    marginBottom: '16px',
  },
  sectionTitle: {
    fontSize: '12px',
    textTransform: 'uppercase',
    color: 'rgba(255, 255, 255, 0.5)',
    marginBottom: '8px',
    letterSpacing: '0.5px',
  },
  presetGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '8px',
  },
  presetButton: {
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '8px',
    padding: '10px 12px',
    cursor: 'pointer',
    textAlign: 'left' as const,
    transition: 'all 0.2s',
    color: 'white',
  },
  presetButtonSelected: {
    background: 'rgba(100, 150, 255, 0.2)',
    borderColor: 'rgba(100, 150, 255, 0.5)',
  },
  presetName: {
    fontWeight: 600,
    fontSize: '13px',
    marginBottom: '2px',
  },
  presetDesc: {
    fontSize: '11px',
    opacity: 0.6,
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    cursor: 'pointer',
    fontSize: '13px',
  },
  checkbox: {
    width: '16px',
    height: '16px',
    cursor: 'pointer',
  },
  customInputs: {
    marginTop: '12px',
    padding: '12px',
    background: 'rgba(255, 255, 255, 0.03)',
    borderRadius: '8px',
  },
  inputRow: {
    display: 'flex',
    gap: '12px',
    marginBottom: '8px',
  },
  inputLabel: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '4px',
    fontSize: '12px',
    color: 'rgba(255, 255, 255, 0.7)',
    flex: 1,
  },
  input: {
    background: 'rgba(0, 0, 0, 0.3)',
    border: '1px solid rgba(255, 255, 255, 0.15)',
    borderRadius: '4px',
    padding: '8px',
    color: 'white',
    fontSize: '13px',
    outline: 'none',
  },
  slider: {
    width: '100%',
    marginTop: '4px',
  },
  sliderValue: {
    fontSize: '12px',
    color: 'rgba(255, 255, 255, 0.5)',
    marginTop: '4px',
  },
  selectionInfo: {
    background: 'rgba(100, 150, 255, 0.1)',
    padding: '10px 12px',
    borderRadius: '6px',
    fontSize: '13px',
    marginBottom: '16px',
  },
  error: {
    background: 'rgba(255, 100, 100, 0.2)',
    border: '1px solid rgba(255, 100, 100, 0.3)',
    padding: '10px 12px',
    borderRadius: '6px',
    fontSize: '13px',
    marginBottom: '16px',
    color: '#ff9999',
  },
  actions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'flex-end',
  },
  clearButton: {
    background: 'rgba(255, 255, 255, 0.1)',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    borderRadius: '6px',
    padding: '10px 16px',
    color: 'white',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 500,
  },
  loadButton: {
    background: 'linear-gradient(135deg, #4a90d9, #357abd)',
    border: 'none',
    borderRadius: '6px',
    padding: '10px 20px',
    color: 'white',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 600,
    transition: 'all 0.2s',
  },
  loadButtonDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  loadingOverlay: {
    position: 'absolute' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(20, 20, 25, 0.9)',
    borderRadius: '12px',
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '16px',
  },
  loadingSpinner: {
    width: '40px',
    height: '40px',
    border: '3px solid rgba(255, 255, 255, 0.1)',
    borderTopColor: '#4a90d9',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  loadingText: {
    textAlign: 'center' as const,
    fontSize: '14px',
  },
  loadingSubtext: {
    fontSize: '12px',
    opacity: 0.6,
  },
  toggleButton: {
    width: '40px',
    height: '40px',
    borderRadius: '8px',
    background: 'rgba(255, 255, 255, 0.1)',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    color: 'white',
    fontSize: '20px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s',
  },
  toggleButtonActive: {
    background: 'rgba(100, 150, 255, 0.2)',
    borderColor: 'rgba(100, 150, 255, 0.4)',
  },
  resolutionRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginTop: '12px',
  },
  resolutionLabel: {
    fontSize: '13px',
    color: 'rgba(255, 255, 255, 0.7)',
    minWidth: '130px',
  },
  resolutionButtons: {
    display: 'flex',
    gap: '4px',
  },
  resolutionButton: {
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.15)',
    borderRadius: '4px',
    padding: '6px 10px',
    color: 'white',
    fontSize: '12px',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  resolutionButtonSelected: {
    background: 'rgba(100, 150, 255, 0.3)',
    borderColor: 'rgba(100, 150, 255, 0.5)',
  },
  resolutionHint: {
    fontSize: '11px',
    color: 'rgba(255, 255, 255, 0.4)',
    marginTop: '6px',
    marginLeft: '142px',
  },
};

// Add CSS animation for spinner
const styleSheet = document.createElement('style');
styleSheet.textContent = `
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;
document.head.appendChild(styleSheet);
