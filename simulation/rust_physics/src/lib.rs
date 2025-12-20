use pyo3::prelude::*;
use rayon::prelude::*;
use std::f32::consts::PI;

/// Drone operational modes
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum DroneMode {
    Idle,
    Takeoff,
    Landing,
    Hover,
    Goto,
    Velocity,
    Monitor,
}

/// Individual drone state and physics
#[derive(Clone)]
pub struct Drone {
    pub id: usize,
    pub pos: [f32; 3],
    pub vel: [f32; 3],
    pub yaw: f32,
    pub yaw_rate: f32,
    pub mode: DroneMode,
    pub target_pos: [f32; 3],
    pub target_vel: [f32; 3],
    pub target_yaw: f32,
    pub battery: f32,
    pub healthy: bool,

    // Monitor mode state
    pub monitor_radius: f32,
    pub monitor_altitude: f32,
    pub monitor_angle: f32,

    // PID state for position control
    pid_integral: [f32; 3],
    pid_prev_error: [f32; 3],
}

impl Drone {
    pub fn new(id: usize, x: f32, y: f32, z: f32) -> Self {
        Self {
            id,
            pos: [x, y, z],
            vel: [0.0, 0.0, 0.0],
            yaw: 0.0,
            yaw_rate: 0.0,
            mode: DroneMode::Idle,
            target_pos: [x, y, z],
            target_vel: [0.0, 0.0, 0.0],
            target_yaw: 0.0,
            battery: 100.0,
            healthy: true,
            monitor_radius: 2.0,
            monitor_altitude: 1.5,
            monitor_angle: 0.0,
            pid_integral: [0.0, 0.0, 0.0],
            pid_prev_error: [0.0, 0.0, 0.0],
        }
    }

    /// Reset PID controller state
    pub fn reset_pid(&mut self) {
        self.pid_integral = [0.0, 0.0, 0.0];
        self.pid_prev_error = [0.0, 0.0, 0.0];
    }

    /// Compute velocity command using PID position control
    fn compute_position_control(&mut self, dt: f32, max_vel: f32) -> [f32; 3] {
        const KP: f32 = 2.0;
        const KI: f32 = 0.01;
        const KD: f32 = 0.5;

        let mut vel_cmd = [0.0f32; 3];

        for i in 0..3 {
            let error = self.target_pos[i] - self.pos[i];

            // Proportional
            let p_term = KP * error;

            // Integral with anti-windup
            self.pid_integral[i] += error * dt;
            self.pid_integral[i] = self.pid_integral[i].clamp(-1.0, 1.0);
            let i_term = KI * self.pid_integral[i];

            // Derivative
            let d_term = if dt > 0.0 {
                KD * (error - self.pid_prev_error[i]) / dt
            } else {
                0.0
            };

            self.pid_prev_error[i] = error;

            vel_cmd[i] = (p_term + i_term + d_term).clamp(-max_vel, max_vel);
        }

        vel_cmd
    }

    /// Update drone physics for one timestep
    pub fn step(&mut self, dt: f32, max_vel: f32, monitor_center: Option<[f32; 3]>, monitor_orbit_speed: f32) {
        match self.mode {
            DroneMode::Idle => {
                // Slow down to stop
                self.vel[0] *= 0.95;
                self.vel[1] *= 0.95;
                self.vel[2] *= 0.95;
            }

            DroneMode::Takeoff | DroneMode::Landing | DroneMode::Goto | DroneMode::Hover => {
                // Position control mode
                let vel_cmd = self.compute_position_control(dt, max_vel);
                self.apply_velocity_control(vel_cmd, dt);

                // Check for mode transitions
                let dist = ((self.target_pos[0] - self.pos[0]).powi(2)
                          + (self.target_pos[1] - self.pos[1]).powi(2)
                          + (self.target_pos[2] - self.pos[2]).powi(2)).sqrt();

                if self.mode == DroneMode::Landing && self.pos[2] < 0.15 {
                    self.mode = DroneMode::Idle;
                    self.vel = [0.0, 0.0, 0.0];
                } else if self.mode == DroneMode::Takeoff && dist < 0.1 {
                    self.mode = DroneMode::Hover;
                }
            }

            DroneMode::Velocity => {
                // Direct velocity control
                self.apply_velocity_control(self.target_vel, dt);
            }

            DroneMode::Monitor => {
                // Orbital surveillance mode
                if let Some(center) = monitor_center {
                    // Update angle
                    self.monitor_angle += monitor_orbit_speed * dt;
                    if self.monitor_angle > 2.0 * PI {
                        self.monitor_angle -= 2.0 * PI;
                    }

                    // Calculate orbital position
                    self.target_pos[0] = center[0] + self.monitor_radius * self.monitor_angle.cos();
                    self.target_pos[1] = center[1] + self.monitor_radius * self.monitor_angle.sin();
                    self.target_pos[2] = self.monitor_altitude;

                    // Face towards center
                    let dx = center[0] - self.target_pos[0];
                    let dy = center[1] - self.target_pos[1];
                    self.target_yaw = dy.atan2(dx);

                    // Use position control to reach orbital position
                    let vel_cmd = self.compute_position_control(dt, max_vel);
                    self.apply_velocity_control(vel_cmd, dt);
                }
            }
        }

        // Update yaw
        let yaw_error = self.target_yaw - self.yaw;
        // Normalize to [-PI, PI]
        let yaw_error = yaw_error.sin().atan2(yaw_error.cos());
        self.yaw_rate = (2.0 * yaw_error).clamp(-PI, PI);
        self.yaw += self.yaw_rate * dt;

        // Clamp position to world bounds
        self.pos[0] = self.pos[0].clamp(-10.0, 10.0);
        self.pos[1] = self.pos[1].clamp(-10.0, 10.0);
        self.pos[2] = self.pos[2].clamp(0.0, 5.0);

        // Update health based on bounds and battery
        self.healthy = self.pos[0].abs() < 15.0
                    && self.pos[1].abs() < 15.0
                    && self.pos[2] >= 0.0
                    && self.pos[2] <= 10.0
                    && self.battery > 0.0;
    }

    /// Apply velocity control with simple dynamics
    fn apply_velocity_control(&mut self, target_vel: [f32; 3], dt: f32) {
        // Velocity response (like a first-order system)
        const RESPONSE_RATE: f32 = 5.0;  // How fast velocity responds
        const DRAG: f32 = 0.1;

        for i in 0..3 {
            let accel = RESPONSE_RATE * (target_vel[i] - self.vel[i]) - DRAG * self.vel[i];
            self.vel[i] += accel * dt;
        }

        // Integrate position
        self.pos[0] += self.vel[0] * dt;
        self.pos[1] += self.vel[1] * dt;
        self.pos[2] += self.vel[2] * dt;
    }
}

/// Python-exposed drone state (for returning to Python)
#[pyclass]
#[derive(Clone)]
pub struct PyDroneState {
    #[pyo3(get)]
    pub id: usize,
    #[pyo3(get)]
    pub pos: [f32; 3],
    #[pyo3(get)]
    pub vel: [f32; 3],
    #[pyo3(get)]
    pub yaw: f32,
    #[pyo3(get)]
    pub battery: f32,
    #[pyo3(get)]
    pub healthy: bool,
}

/// The main swarm physics engine
#[pyclass]
pub struct RustSwarm {
    drones: Vec<Drone>,
    sim_time: f32,
    physics_dt: f32,
    max_velocity: f32,
    speed_multiplier: f32,
    monitor_center: Option<[f32; 3]>,
    monitor_orbit_speed: f32,
}

#[pymethods]
impl RustSwarm {
    #[new]
    #[pyo3(signature = (num_drones, physics_hz=240))]
    pub fn new(num_drones: usize, physics_hz: u32) -> Self {
        let grid_size = (num_drones as f32).sqrt().ceil() as usize;
        let spacing = 0.5;

        let mut drones = Vec::with_capacity(num_drones);
        for i in 0..num_drones {
            let row = i / grid_size;
            let col = i % grid_size;
            let x = (col as f32 - grid_size as f32 / 2.0) * spacing;
            let y = (row as f32 - grid_size as f32 / 2.0) * spacing;
            let z = 0.1;
            drones.push(Drone::new(i, x, y, z));
        }

        Self {
            drones,
            sim_time: 0.0,
            physics_dt: 1.0 / physics_hz as f32,
            max_velocity: 2.0,
            speed_multiplier: 1.0,
            monitor_center: None,
            monitor_orbit_speed: 0.3,
        }
    }

    /// Step physics for all drones (parallelized with rayon)
    pub fn step(&mut self) -> f32 {
        let dt = self.physics_dt;
        let max_vel = self.max_velocity * self.speed_multiplier;
        let monitor_center = self.monitor_center;
        let monitor_orbit_speed = self.monitor_orbit_speed;

        // Parallel update of all drones
        self.drones.par_iter_mut().for_each(|drone| {
            drone.step(dt, max_vel, monitor_center, monitor_orbit_speed);
        });

        self.sim_time += dt;
        self.sim_time
    }

    /// Step physics multiple times (for speed multiplier)
    pub fn step_multiple(&mut self, steps: u32) -> f32 {
        for _ in 0..steps {
            self.step();
        }
        self.sim_time
    }

    /// Get all drone states
    pub fn get_states(&self) -> Vec<PyDroneState> {
        self.drones.iter().map(|d| PyDroneState {
            id: d.id,
            pos: d.pos,
            vel: d.vel,
            yaw: d.yaw,
            battery: d.battery,
            healthy: d.healthy,
        }).collect()
    }

    /// Get simulation time
    pub fn get_time(&self) -> f32 {
        self.sim_time
    }

    /// Get number of drones
    pub fn num_drones(&self) -> usize {
        self.drones.len()
    }

    /// Set speed multiplier
    pub fn set_speed(&mut self, multiplier: f32) {
        self.speed_multiplier = multiplier;
        self.max_velocity = 2.0 * multiplier;
    }

    /// Command: Takeoff
    #[pyo3(signature = (ids, altitude=1.0))]
    pub fn takeoff(&mut self, ids: Vec<usize>, altitude: f32) {
        for &id in &ids {
            if id < self.drones.len() {
                let drone = &mut self.drones[id];
                drone.target_pos = [drone.pos[0], drone.pos[1], altitude];
                drone.target_yaw = 0.0;
                drone.mode = DroneMode::Takeoff;
                drone.reset_pid();
            }
        }
    }

    /// Command: Takeoff all
    #[pyo3(signature = (altitude=1.0))]
    pub fn takeoff_all(&mut self, altitude: f32) {
        let ids: Vec<usize> = (0..self.drones.len()).collect();
        self.takeoff(ids, altitude);
    }

    /// Command: Land
    pub fn land(&mut self, ids: Vec<usize>) {
        for &id in &ids {
            if id < self.drones.len() {
                let drone = &mut self.drones[id];
                drone.target_pos = [drone.pos[0], drone.pos[1], 0.05];
                drone.target_yaw = 0.0;
                drone.mode = DroneMode::Landing;
                drone.reset_pid();
            }
        }
    }

    /// Command: Land all
    pub fn land_all(&mut self) {
        let ids: Vec<usize> = (0..self.drones.len()).collect();
        self.land(ids);
    }

    /// Command: Hover
    pub fn hover(&mut self, ids: Vec<usize>) {
        for &id in &ids {
            if id < self.drones.len() {
                let drone = &mut self.drones[id];
                drone.target_pos = drone.pos;
                drone.target_yaw = drone.yaw;
                drone.mode = DroneMode::Hover;
            }
        }
    }

    /// Command: Hover all
    pub fn hover_all(&mut self) {
        let ids: Vec<usize> = (0..self.drones.len()).collect();
        self.hover(ids);
    }

    /// Command: Goto position
    #[pyo3(signature = (id, x, y, z, yaw=0.0))]
    pub fn goto(&mut self, id: usize, x: f32, y: f32, z: f32, yaw: f32) {
        if id < self.drones.len() {
            let drone = &mut self.drones[id];
            drone.target_pos = [
                x.clamp(-10.0, 10.0),
                y.clamp(-10.0, 10.0),
                z.clamp(0.1, 5.0),
            ];
            drone.target_yaw = yaw;
            drone.mode = DroneMode::Goto;
            drone.reset_pid();
        }
    }

    /// Command: Set velocity
    #[pyo3(signature = (id, vx, vy, vz, yaw_rate=0.0))]
    pub fn velocity(&mut self, id: usize, vx: f32, vy: f32, vz: f32, yaw_rate: f32) {
        if id < self.drones.len() {
            let drone = &mut self.drones[id];
            let max_v = 2.0;
            drone.target_vel = [
                vx.clamp(-max_v, max_v),
                vy.clamp(-max_v, max_v),
                vz.clamp(-max_v, max_v),
            ];
            drone.yaw_rate = yaw_rate.clamp(-PI, PI);
            drone.mode = DroneMode::Velocity;
        }
    }

    /// Command: Formation - Line
    #[pyo3(signature = (center, spacing=1.0, axis="x"))]
    pub fn formation_line(&mut self, center: [f32; 3], spacing: f32, axis: &str) {
        let n = self.drones.len();
        let start_offset = -((n - 1) as f32) * spacing / 2.0;

        for i in 0..n {
            let offset = start_offset + i as f32 * spacing;
            let (x, y) = match axis {
                "x" => (center[0] + offset, center[1]),
                "y" => (center[0], center[1] + offset),
                _ => (center[0] + offset, center[1]),
            };
            self.goto(i, x, y, center[2], 0.0);
        }
    }

    /// Command: Formation - Circle
    #[pyo3(signature = (center, radius=1.5))]
    pub fn formation_circle(&mut self, center: [f32; 3], radius: f32) {
        let n = self.drones.len();
        for i in 0..n {
            let angle = 2.0 * PI * i as f32 / n as f32;
            let x = center[0] + radius * angle.cos();
            let y = center[1] + radius * angle.sin();
            self.goto(i, x, y, center[2], 0.0);
        }
    }

    /// Command: Formation - Grid
    #[pyo3(signature = (center, spacing=1.0))]
    pub fn formation_grid(&mut self, center: [f32; 3], spacing: f32) {
        let n = self.drones.len();
        let cols = (n as f32).sqrt().ceil() as usize;
        let rows = (n + cols - 1) / cols;

        let start_x = -((cols - 1) as f32) * spacing / 2.0;
        let start_y = -((rows - 1) as f32) * spacing / 2.0;

        for i in 0..n {
            let row = i / cols;
            let col = i % cols;
            let x = center[0] + start_x + col as f32 * spacing;
            let y = center[1] + start_y + row as f32 * spacing;
            self.goto(i, x, y, center[2], 0.0);
        }
    }

    /// Command: Formation - V shape
    #[pyo3(signature = (center, spacing=1.0))]
    pub fn formation_v(&mut self, center: [f32; 3], spacing: f32) {
        let n = self.drones.len();
        let angle: f32 = PI / 6.0;  // 30 degrees

        // Leader at front
        if n > 0 {
            self.goto(0, center[0], center[1], center[2], 0.0);
        }

        // Followers in V behind
        for i in 1..n {
            let side = if i % 2 == 0 { 1.0 } else { -1.0 };
            let offset_back = ((i + 1) / 2) as f32;

            let x = center[0] - offset_back * spacing * angle.cos();
            let y = center[1] + side * offset_back * spacing * angle.sin();
            self.goto(i, x, y, center[2], 0.0);
        }
    }

    /// Command: Waypoint - all drones go to formation around point
    #[pyo3(signature = (x, y, z))]
    pub fn waypoint(&mut self, x: f32, y: f32, z: f32) {
        let center = [x, y, z];
        let radius = 0.8;

        if self.drones.len() == 1 {
            self.goto(0, x, y, z, 0.0);
        } else {
            self.formation_circle(center, radius);
        }
    }

    /// Command: Monitor mode - orbital surveillance
    #[pyo3(signature = (x, y, z))]
    pub fn monitor(&mut self, x: f32, y: f32, z: f32) {
        self.monitor_center = Some([x, y, z]);

        let n = self.drones.len();
        for i in 0..n {
            let drone = &mut self.drones[i];

            // Vary radius: 1.0 to 3.0
            let radius_factor = (i % 3) as f32 / 2.0;
            drone.monitor_radius = 1.0 + radius_factor * 2.0;

            // Vary altitude
            let altitude_layers = n.min(5);
            let layer = i % altitude_layers;
            let altitude_offset = (layer as f32 - altitude_layers as f32 / 2.0) * 0.6;
            drone.monitor_altitude = (z + altitude_offset).max(0.5);

            // Starting angle
            drone.monitor_angle = 2.0 * PI * i as f32 / n as f32;

            drone.mode = DroneMode::Monitor;
            drone.reset_pid();
        }
    }

    /// Command: Reset simulation
    pub fn reset(&mut self) {
        let num_drones = self.drones.len();
        let grid_size = (num_drones as f32).sqrt().ceil() as usize;
        let spacing = 0.5;

        for i in 0..num_drones {
            let row = i / grid_size;
            let col = i % grid_size;
            let x = (col as f32 - grid_size as f32 / 2.0) * spacing;
            let y = (row as f32 - grid_size as f32 / 2.0) * spacing;

            let drone = &mut self.drones[i];
            drone.pos = [x, y, 0.1];
            drone.vel = [0.0, 0.0, 0.0];
            drone.yaw = 0.0;
            drone.yaw_rate = 0.0;
            drone.mode = DroneMode::Idle;
            drone.battery = 100.0;
            drone.healthy = true;
            drone.reset_pid();
        }

        self.sim_time = 0.0;
        self.monitor_center = None;
    }

    /// Respawn with new drone count
    pub fn respawn(&mut self, num_drones: usize) {
        let grid_size = (num_drones as f32).sqrt().ceil() as usize;
        let spacing = 0.5;

        self.drones.clear();
        for i in 0..num_drones {
            let row = i / grid_size;
            let col = i % grid_size;
            let x = (col as f32 - grid_size as f32 / 2.0) * spacing;
            let y = (row as f32 - grid_size as f32 / 2.0) * spacing;
            let z = 0.1;
            self.drones.push(Drone::new(i, x, y, z));
        }

        self.sim_time = 0.0;
        self.monitor_center = None;
    }

    /// Update battery levels (call once per second)
    pub fn update_batteries(&mut self, drain_rate: f32) {
        for drone in &mut self.drones {
            if drone.mode != DroneMode::Idle {
                drone.battery = (drone.battery - drain_rate / 60.0).max(0.0);
            }
        }
    }
}

/// Python module
#[pymodule]
fn drone_physics(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RustSwarm>()?;
    m.add_class::<PyDroneState>()?;
    Ok(())
}
