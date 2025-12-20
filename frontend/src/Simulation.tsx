import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';

interface DroneState {
  id: number;
  pos: [number, number, number];
  // Add other properties from the state if needed
}

interface SimulationState {
  drones: DroneState[];
  // Add other properties from the state if needed
}

interface SimulationProps {
  simulationState: SimulationState | null;
}

const Simulation: React.FC<SimulationProps> = ({ simulationState }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const dronesRef = useRef<THREE.Mesh[]>([]);

  useEffect(() => {
    if (!mountRef.current) return;

    // Scene
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(75, mountRef.current.clientWidth / mountRef.current.clientHeight, 0.1, 1000);
    camera.position.z = 10;
    camera.position.y = 5;
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer();
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    rendererRef.current = renderer;
    mountRef.current.appendChild(renderer.domElement);

    // Ground
    const groundGeometry = new THREE.PlaneGeometry(20, 20);
    const groundMaterial = new THREE.MeshBasicMaterial({ color: 0xcccccc, side: THREE.DoubleSide });
    const ground = new THREE.Mesh(groundGeometry, groundMaterial);
    ground.rotation.x = Math.PI / 2;
    scene.add(ground);

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };

    animate();

    // Handle resize
    const handleResize = () => {
      if (mountRef.current && rendererRef.current && cameraRef.current) {
        camera.aspect = mountRef.current.clientWidth / mountRef.current.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
      }
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      if (mountRef.current && rendererRef.current) {
        mountRef.current.removeChild(rendererRef.current.domElement);
      }
    };
  }, []);

  useEffect(() => {
    if (!simulationState || !sceneRef.current) return;

    // Add or remove drones
    if (simulationState.drones.length !== dronesRef.current.length) {
      // Remove all drones
      dronesRef.current.forEach(drone => sceneRef.current?.remove(drone));
      dronesRef.current = [];

      // Add new drones
      simulationState.drones.forEach(droneState => {
        const geometry = new THREE.BoxGeometry(0.5, 0.5, 0.5);
        const material = new THREE.MeshBasicMaterial({ color: 0x00ff00 });
        const cube = new THREE.Mesh(geometry, material);
        sceneRef.current?.add(cube);
        dronesRef.current.push(cube);
      });
    }

    // Update drone positions
    simulationState.drones.forEach((droneState, index) => {
      if (dronesRef.current[index]) {
        dronesRef.current[index].position.set(droneState.pos[0], droneState.pos[2], -droneState.pos[1]);
      }
    });

  }, [simulationState]);

  return <div ref={mountRef} style={{ width: '100%', height: '100%' }} />;
};

export default Simulation;
