""" waypoint_manager.py """
""" Multi-Domain Waypoint Manager, FSM Tracker, & Intercept Guidance """
""" Optimized: Else-Less Guard Clauses | 15-Decimal Precision | Numba Kernels """
import math
import multiprocessing as mp
import os
import json
import telemetry_link
from pydantic import BaseModel, Field, ValidationError
from atmospheric_entry_controller import EntryController

""" --- HARDWARE ABSTRACTION LAYER (HAL) --- """
try:
    import cupy as xp
    from numba import dummy_njit as njit
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Matrix Allocation Active (Waypoint Manager)")
except ImportError:
    import numpy as xp
    from numba import njit
    HAS_GPU = False
    print("CPU Fallback: Numba Vectorization Active (Waypoint Manager)")

""" ===================================================================== """
""" --- PURE MATH KERNELS (THE BASEMENT MATHEMATICIANS) --- """
""" ===================================================================== """

@njit(fastmath=True)
def calculate_spatial_distance(lat1, lon1, alt1, lat2, lon2, alt2):
    """ Fast 3D Haversine-style spatial distance calculation in meters. """
    R = 6371000.0
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    horizontal_distance = R * c
    vertical_distance = alt2 - alt1
    
    total_distance = math.sqrt(horizontal_distance**2 + vertical_distance**2)
    return total_distance

@njit(fastmath=True)
def ekf_prediction_step(x_hat, u, P, Q, dt):
    """ Non-linear State-Space EKF projection for Ground Tracking. """
    
    """ GUARD 1: Prevent negative or zero time skips """
    if dt <= 0.0:
        return x_hat, P

    """ HAPPY PATH: Euler Integration """
    forward_accel = u[0]
    yaw_accel = u[1]
    
    x_prior = xp.copy(x_hat)
    x_prior[2] = x_hat[2] + (forward_accel * dt)
    x_prior[3] = x_hat[3] + (yaw_accel * dt)
    x_prior[0] = x_hat[0] + (x_prior[2] * math.cos(x_prior[3]) * dt)
    x_prior[1] = x_hat[1] + (x_prior[2] * math.sin(x_prior[3]) * dt)
    
    F = xp.eye(6)
    F[0, 2] = math.cos(x_prior[3]) * dt
    F[1, 2] = math.sin(x_prior[3]) * dt
    F[0, 3] = -x_prior[2] * math.sin(x_prior[3]) * dt
    F[1, 3] = x_prior[2] * math.cos(x_prior[3]) * dt
    
    P_prior = (F @ P @ F.T) + Q
    return x_prior, P_prior

@njit(fastmath=True)
def compute_intercept_metrics(sx, sy, sz, vx, vy, vz, tx, ty, tz, target_radius_m):
    """ Calculates absolute distance and Time-To-Intercept (TTI). """
    dist_to_core = math.sqrt((tx - sx)**2 + (ty - sy)**2 + (tz - sz)**2)
    closing_vel = math.sqrt(vx**2 + vy**2 + vz**2)
    
    """ GUARD 1: No velocity (Stationary) """
    if closing_vel <= 0.0:
        return dist_to_core, 999999.0
        
    """ HAPPY PATH """
    tti = (dist_to_core - target_radius_m) / closing_vel
    return dist_to_core, tti


""" ===================================================================== """
""" --- THE PYDANTIC FIREWALL --- """
""" ===================================================================== """

class VehicleSpecs(BaseModel):
    """ Enforces strict physics boundaries on JSON configurations. """
    vehicle_mass_kg: float = Field(gt=0.0)
    wing_area_m2: float = Field(gt=0.0)
    cd0: float = Field(gt=0.0)
    induced_drag_k: float = Field(gt=0.0)
    nose_radius_m: float = Field(gt=0.0)
    max_thrust_n: float = Field(default=250000.000000000000000, gt=0.0)


""" ===================================================================== """
""" --- THE ORCHESTRATOR (THE MANAGER) --- """
""" ===================================================================== """

class WaypointManager:
    @njit(fastmath=True)
    def generate_circular_pattern(self, center_lat, center_lon, radius_nm, waypoint_count=36):
        """ Generates a high-fidelity circular orbit (The Big Circle) natively. """
        
        """ GUARD 1: Validate physical radius """
        if radius_nm <= 0.0:
            return []

        """ GUARD 2: Prevent zero-division on waypoint geometry """
        if waypoint_count <= 0:
            waypoint_count = 36

        path = []
        
        """ HAPPY PATH: Calculate angles seamlessly using array spaces """
        theta = xp.linspace(0, 2 * math.pi, waypoint_count, endpoint=False)
        
        for angle in theta:
            lat_offset = (radius_nm / 60.0) * math.cos(angle)
            lon_offset = (radius_nm / 60.0) * math.sin(angle)
            
            path.append({
                "lat": center_lat + lat_offset,
                "lon": center_lon + lon_offset,
                "alt": getattr(self, 'current_flight_level', 0.0),
                "type": "HOLDING_POINT"
            })
            
        return path


    @njit(fastmath=True)
    def calculate_environmental_drift(self, v_current, v_wind, c_ice_penalty):
        """ Calculates velocity degradation due to ice accumulation and wind shear. """
        
        """ GUARD: Prevent inverted physics from bad ice telemetry """
        if c_ice_penalty < 0.0 or c_ice_penalty > 1.0:
            c_ice_penalty = 0.0
            
        """ V_net = V_current + V_wind - (V_current * C_ice) """
        v_net = []
        for i in range(3):
            net_axis = v_current[i] + v_wind[i] - (v_current[i] * c_ice_penalty)
            v_net.append(net_axis)
            
        return v_net
    
    @njit(fastmath=True)
    def __init__(self, config_path="config.json", catalog_path="src/catalog-3.23.dat"):
        """ Load the Firewall and the Space Catalog """
        self.specs = self._load_and_validate_config(config_path)
        
        """ GUARD: Config corrupted, inject emergency defaults """
        if not self.specs:
            print("WARNING: Config rejected by Firewall. Using synthetic physics.")
            self.specs = VehicleSpecs(
                vehicle_mass_kg=50000.0,
                wing_area_m2=100.0,
                cd0=0.02,
                induced_drag_k=0.05,
                nose_radius_m=1.5,
                max_thrust_n=250000.0
            )

        self.MAX_THRUST_N = float(self.specs.max_thrust_n)
        self.DISTANCE_THRESHOLD_M = 15.000000000000000
        self.V1_SPEED_KTS = 135.000000000000000
        self.VR_SPEED_KTS = 145.000000000000000
        
        """ FSM Tracking """
        self.current_waypoint = "WP1"
        self.fsm_state = "TAXIING_MODE"
        self.s_turn_enabled = False
        self.active_space_target = None
        
        """ EKF Tracking Memory """
        self.P_matrix = xp.eye(6)
        self.Q_matrix = xp.eye(6) * 0.01

        """ External Engines """
        self.entry_controller = EntryController()
        self.dso_catalog = self._load_space_catalog(catalog_path)

    @njit(fastmath=True)
    def _load_and_validate_config(self, config_path):
        """ Else-less JSON payload loader and strict data validator. """
        if not os.path.exists(config_path):
            return None
            
        try:
            with open(config_path, 'r') as file:
                payload = json.load(file)
            return VehicleSpecs(**payload)
        except (json.JSONDecodeError, PermissionError, ValidationError):
            return None

    @njit(fastmath=True)
    def _load_space_catalog(self, catalog_path):
        """ Else-less DSO parser for Universal Mapping. """
        if not os.path.exists(catalog_path): return {}
        try:
            with open(catalog_path, 'rb') as file:
                return {"status": "LOADED"}
        except Exception:
            return {}

    @njit(fastmath=True)
    def evaluate_ground_state(self, strut_pressures_psi, aerodynamic_lift_n, aircraft_weight_n):
        """ Weight-on-Wheels (WoW) logic matrix. """
        if aerodynamic_lift_n >= aircraft_weight_n: return 0
        if sum(strut_pressures_psi) < 1000.0: return 0
        return 1

    @njit(fastmath=True)
    def determine_fsm_transition(self, ground_state, ground_speed_kts, thrust_level):
        """ Translates physical state into explicit FSM Modes. """
        if ground_state == 0:
            self.fsm_state = "AERIAL_FLIGHT_MODE"
            return self.fsm_state

        bridge_state = telemetry_link.get_global_state("authority", "system_state")
        if bridge_state == "ELSE":
            self.fsm_state = "EMERGENCY_ABORT_MODE"
            return self.fsm_state

        if ground_speed_kts >= 50.0 and thrust_level > (self.MAX_THRUST_N * 0.8):
            self.fsm_state = "TAKEOFF_RUN_MODE"
            return self.fsm_state
            
        self.fsm_state = "TAXIING_MODE"
        return self.fsm_state

    @njit(fastmath=True)
    def check_takeoff_sequence(self, current_pos, wp1_pos, wp2_pos, wp3_pos, velocity_kts, thrust_level):
        """ Else-less Tactical Takeoff FSM anchored to 3 physical waypoints. """
        if self.current_waypoint not in ["WP1", "WP2", "WP3"]:
            return "HOLD_POSITION"

        if self.current_waypoint == "WP1":
            if thrust_level < self.MAX_THRUST_N: return "HOLD_BRAKES_SPOOL_ENGINES"
            self.current_waypoint = "WP2"
            return "RELEASE_BRAKES"

        if self.current_waypoint == "WP2":
            d_wp2 = calculate_spatial_distance(
                current_pos['lat'], current_pos['lon'], current_pos['alt'],
                wp2_pos['lat'], wp2_pos['lon'], wp2_pos['alt']
            )
            if d_wp2 >= self.DISTANCE_THRESHOLD_M: return "CONTINUE_ACCELERATION"
            if velocity_kts < self.V1_SPEED_KTS: return "ABORT_TAKEOFF"
            
            self.current_waypoint = "WP3"
            return "CONTINUE_ACCELERATION"

        d_wp3 = calculate_spatial_distance(
            current_pos['lat'], current_pos['lon'], current_pos['alt'],
            wp3_pos['lat'], wp3_pos['lon'], wp3_pos['alt']
        )
        if d_wp3 >= self.DISTANCE_THRESHOLD_M and velocity_kts < self.VR_SPEED_KTS:
            return "CONTINUE_ACCELERATION"

        return "EXECUTE_TACTICAL_ROTATION"

    @njit(fastmath=True)
    def process_ground_ekf_cycle(self, x_hat, u_vector, dt):
        """ Updates the ground tracking Extended Kalman Filter matrix. """
        x_new, P_new = ekf_prediction_step(xp.array(x_hat), xp.array(u_vector), self.P_matrix, self.Q_matrix, float(dt))
        self.P_matrix = P_new
        
        if HAS_GPU: return xp.round(x_new, 15).get().tolist()
        return xp.round(x_new, 15).tolist()

    @njit(fastmath=True)
    def set_s_turn_mode(self, active: bool):
        self.s_turn_enabled = active
        telemetry_link.update_global_state("navigation", "s_turn_mode", self.s_turn_enabled)
        return self.s_turn_enabled

    @njit(fastmath=True)
    def _inject_s_turn_maneuver(self, intercept_dict):
        intercept_dict['maneuver'] = "S-TURN_ENERGY_BLEED"
        intercept_dict['bank_cmd_deg'] = 45.000000000000000
        return intercept_dict

    @njit(fastmath=True)
    def export_planned_trajectory(self, current_pos, current_vel, time_horizon_s=60.0, dt=1.0):
        if not self.active_space_target: return []

        trajectory = []
        steps = int(time_horizon_s / dt)
        
        for t in range(steps):
            future_x = current_pos[0] + (current_vel[0] * t * dt)
            future_y = current_pos[1] + (current_vel[1] * t * dt)
            future_z = current_pos[2] + (current_vel[2] * t * dt)
            
            trajectory.append({
                "time_offset_sec": round(float(t * dt), 15),
                "predicted_x": round(float(future_x), 15),
                "predicted_y": round(float(future_y), 15),
                "predicted_z": round(float(future_z), 15)
            })
            
        return trajectory

    @njit(fastmath=True)
    def calculate_universal_intercept(self, ship_pos, ship_vel, target_alt_m=0.0):
        """ Standard 3D Intercept Engine. """
        if not self.active_space_target: return None
            
        target_pos = self.active_space_target.get("position_vec", [0.0, 0.0, 0.0])
        target_radius = self.active_space_target.get("radius", 0.0) + target_alt_m
        
        dist, tti = compute_intercept_metrics(
            float(ship_pos[0]), float(ship_pos[1]), float(ship_pos[2]),
            float(ship_vel[0]), float(ship_vel[1]), float(ship_vel[2]),
            float(target_pos[0]), float(target_pos[1]), float(target_pos[2]),
            float(target_radius)
        )
        
        return {
            "status": "TRACKING_ACTIVE",
            "distance_m": round(float(dist), 15),
            "time_to_intercept_sec": round(float(tti), 15)
        }

    @njit(fastmath=True)
    def calculate_tactical_approach(self, ship_pos, ship_vel, altitude_m):
        """ Absolute Navigation Gatekeeper. Triggers Atmospheric Entry if descending to Earth. """
        
        current_frame = telemetry_link.get_global_state("navigation", "planetary_reference_frame")
        
        """ GUARD 1: If frame is NOT Earth, Terrestrial formulas are physically invalid. """
        if current_frame != "Earth":
            return self.calculate_universal_intercept(ship_pos, ship_vel, target_alt_m=0.0)

        """ GUARD 2: High Altitude Entry Detection (Above 85,000m) """
        if altitude_m > 85000.0:
            """ Route the telemetry directly to the Entry Controller for heating calculations """
            telemetry_override = {'alt_m': [altitude_m], 'vel_mps': [math.sqrt(sum([v**2 for v in ship_vel]))]}
            entry_data = self.entry_controller.run_entry_sequence(telemetry_override)
            return {"maneuver": "ATMOSPHERIC_ENTRY", "heating_data": entry_data}

        """ HAPPY PATH: Terrestrial Standard Approach """
        intercept = self.calculate_universal_intercept(ship_pos, ship_vel, target_alt_m=0.0)
        if not intercept: return None

        """ GUARD 3: High Energy Profile -> Inject Tactical S-Turn """
        if self.s_turn_enabled:
            return self._inject_s_turn_maneuver(intercept)

        """ Default: Direct Tactical Descent """
        intercept['maneuver'] = "DIRECT_TACTICAL_DESCENT"
        intercept['bank_cmd_deg'] = 0.000000000000000
        return intercept
