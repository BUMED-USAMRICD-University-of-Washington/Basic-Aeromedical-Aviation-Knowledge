import multiprocessing as mp
""" waypoint_manager.py """
""" Multi-Domain Waypoint Manager, FSM Tracker, & Intercept Guidance """
""" Optimized: Else-Less Guard Clauses | 15-Decimal Precision | Numba Kernels """

import math
import os
import json
import telemetry_link

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
""" These receive @njit because they only process pure numbers and arrays """
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
""" --- THE ORCHESTRATOR (THE MANAGER) --- """
""" NO @njit here. Interacts with FSM classes, state, files, and telemetry. """
""" ===================================================================== """

class WaypointManager:
    """ Manages FSM, Tactical Takeoff Sequence, and 3D Universal Routing. """
    
    def __init__(self, config_path="config.json", catalog_path="src/catalog-3.23.dat"):
        """ 15-Decimal Default Thresholds """
        self.DISTANCE_THRESHOLD_M = 15.000000000000000
        self.V1_SPEED_KTS = 135.000000000000000
        self.VR_SPEED_KTS = 145.000000000000000
        self.MAX_THRUST_N = 250000.000000000000000
        
        self.current_waypoint = "WP1"
        self.fsm_state = "TAXIING_MODE"
        
        """ EKF Tracking Memory """
        self.P_matrix = xp.eye(6)
        self.Q_matrix = xp.eye(6) * 0.01

        """ FSM Feature Flags """
        self.s_turn_enabled = False
        """ Tactical takeoff and landing are the default active profiles """
        self.active_space_target = None

        """ System Initialization """
        self.config = self._load_and_validate_config(config_path)
        self.dso_catalog = self._load_space_catalog(catalog_path)

    def _load_and_validate_config(self, config_path):
        """ Else-less JSON payload configuration loader. """
        
        """ GUARD 1: File missing """
        if not os.path.exists(config_path):
            return {}
            
        """ GUARD 2: JSON Corruption / Read Collision """
        try:
            with open(config_path, 'r') as file:
                payload = json.load(file)
        except (json.JSONDecodeError, PermissionError):
            return {}
            
        """ HAPPY PATH """
        return payload

    def _load_space_catalog(self, catalog_path):
        """ Else-less DSO parser for Universal Mapping. """
        
        """ GUARD 1: Catalog missing """
        if not os.path.exists(catalog_path):
            return {}
            
        """ HAPPY PATH: Load Stellarium Database """
        catalog = {}
        try:
            with open(catalog_path, 'rb') as file:
                """ Dummy read for architecture completion. """
                """ Full byte-parsing delegated to stellarium_parser.py """
                catalog["status"] = "LOADED"
        except Exception:
            return {}
            
        return catalog

    def set_s_turn_mode(self, active: bool):
        """ Explicit mode toggle for energy bleed S-Turns. """
        self.s_turn_enabled = active
        telemetry_link.update_global_state("navigation", "s_turn_mode", self.s_turn_enabled)
        return self.s_turn_enabled

    def _inject_s_turn_maneuver(self, intercept_dict):
        """ Creates lateral bank commands to bleed airspeed energy safely. """
        intercept_dict['maneuver'] = "S-TURN_ENERGY_BLEED"
        intercept_dict['bank_cmd_deg'] = 45.000000000000000
        return intercept_dict

    def export_planned_trajectory(self, current_pos, current_vel, time_horizon_s=60.0, dt=1.0):
        """ Projects the current intercept vector forward for autonomous intent analysis. """
        
        """ GUARD 1: No active target selected """
        if not self.active_space_target:
            return []

        """ HAPPY PATH: Linear kinematic projection """
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

    def calculate_universal_intercept(self, ship_pos, ship_vel, target_alt_m=0.0):
        """ Standard 3D Intercept Engine (Core Navigation). """
        
        """ GUARD 1: No active target to intercept """
        if not self.active_space_target:
            return None
            
        target_pos = self.active_space_target.get("position_vec", [0.0, 0.0, 0.0])
        target_radius = self.active_space_target.get("radius", 0.0) + target_alt_m
        
        """ Call Numba Math Kernel """
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

    def calculate_tactical_approach(self, ship_pos, ship_vel, target_lat, target_lon):
        """ Absolute Navigation Gatekeeper. Isolates Earth physics from Space physics. """
        
        current_frame = telemetry_link.get_global_state("navigation", "planetary_reference_frame")
        
        """ GUARD 1: If frame is NOT Earth, Terrestrial formulas are physically invalid. """
        if current_frame != "Earth":
            return self.calculate_universal_intercept(ship_pos, ship_vel, target_alt_m=0.0)

        """ HAPPY PATH: Terrestrial Standard Approach """
        intercept = self.calculate_universal_intercept(ship_pos, ship_vel, target_alt_m=0.0)
        
        """ GUARD 2: Intercept dropped due to missing target lock """
        if not intercept:
            return None

        """ GUARD 3: High Energy Profile -> Inject Tactical S-Turn """
        if self.s_turn_enabled:
            return self._inject_s_turn_maneuver(intercept)

        """ Default: Direct Tactical Descent """
        intercept['maneuver'] = "DIRECT_TACTICAL_DESCENT"
        intercept['bank_cmd_deg'] = 0.000000000000000
        return intercept
