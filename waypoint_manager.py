import multiprocessing as mp
import os
""" waypoint_manager.py """
""" Finite State Machine & Ground-to-Air Sequence Tracker """
""" Optimized: Else-Less Guard Clauses | 15-Decimal Precision | Numba Kernels """

import math
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
    
    """ 1. Constant Default (Earth Radius in meters) """
    R = 6371000.0
    
    """ HAPPY PATH: Spherical distance computation """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    horizontal_distance = R * c
    vertical_distance = alt2 - alt1
    
    """ 3D Euclidean distance including elevation """
    total_distance = math.sqrt(horizontal_distance**2 + vertical_distance**2)
    return total_distance


@njit(fastmath=True)
def ekf_prediction_step(x_hat, u, P, Q, dt):
    """ Non-linear State-Space EKF projection for Ground Tracking. """
    """ State x: [x, y, V, psi, theta, q] """
    
    """ GUARD 1: Prevent negative or zero time skips """
    if dt <= 0.0:
        return x_hat, P

    """ HAPPY PATH: Project state forward (Euler Integration) """
    """ For pure math abstraction, we treat u[0] as forward acceleration, u[1] as yaw acceleration """
    forward_accel = u[0]
    yaw_accel = u[1]
    
    x_prior = xp.copy(x_hat)
    
    """ Update Velocity and Heading """
    x_prior[2] = x_hat[2] + (forward_accel * dt)
    x_prior[3] = x_hat[3] + (yaw_accel * dt)
    
    """ Update X/Y ground coordinates based on new velocity and heading """
    x_prior[0] = x_hat[0] + (x_prior[2] * math.cos(x_prior[3]) * dt)
    x_prior[1] = x_hat[1] + (x_prior[2] * math.sin(x_prior[3]) * dt)
    
    """ Jacobian approximation (F) for covariance projection """
    """ Equation: P_prior = F * P * F^T + Q """
    F = xp.eye(6)
    F[0, 2] = math.cos(x_prior[3]) * dt
    F[1, 2] = math.sin(x_prior[3]) * dt
    F[0, 3] = -x_prior[2] * math.sin(x_prior[3]) * dt
    F[1, 3] = x_prior[2] * math.cos(x_prior[3]) * dt
    
    P_prior = (F @ P @ F.T) + Q
    
    return x_prior, P_prior


""" ===================================================================== """
""" --- THE ORCHESTRATOR (THE MANAGER) --- """
""" NO @njit here. This interacts with FSM classes, state, and telemetry. """
""" ===================================================================== """

class WaypointManager:
    """ Manages the Ground FSM, Tactical Takeoff Sequence, and 3D Waypoint Routing. """
    
    def __init__(self):
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

    def evaluate_ground_state(self, strut_pressures_psi, aerodynamic_lift_n, aircraft_weight_n):
        """ Weight-on-Wheels (WoW) logic matrix. """
        
        """ GUARD 1: Lift exceeds weight (Airborne) """
        if aerodynamic_lift_n >= aircraft_weight_n:
            return 0
            
        """ GUARD 2: Strut pressure is zero/low (Gear in transit or freely hanging) """
        pressure_sum = sum(strut_pressures_psi)
        if pressure_sum < 1000.0:
            return 0
            
        """ HAPPY PATH: Solidly on the runway surface """
        return 1

    def determine_fsm_transition(self, ground_state, ground_speed_kts, thrust_level):
        """ Translates physical state into explicit FSM Modes. """
        
        """ GUARD 1: Airborne """
        if ground_state == 0:
            self.fsm_state = "AERIAL_FLIGHT_MODE"
            return self.fsm_state

        """ GUARD 2: Emergency Abort trigger from Telemetry Bridge """
        bridge_state = telemetry_link.get_global_state("authority", "system_state")
        if bridge_state == "ELSE":
            self.fsm_state = "EMERGENCY_ABORT_MODE"
            return self.fsm_state

        """ GUARD 3: Fast Ground Roll (Takeoff Commenced) """
        if ground_speed_kts >= 50.0 and thrust_level > (self.MAX_THRUST_N * 0.8):
            self.fsm_state = "TAKEOFF_RUN_MODE"
            return self.fsm_state
            
        """ HAPPY PATH: Standard Ground Taxi """
        self.fsm_state = "TAXIING_MODE"
        return self.fsm_state

    def check_takeoff_sequence(self, current_pos, wp1_pos, wp2_pos, wp3_pos, velocity_kts, thrust_level):
        """ Else-less Tactical Takeoff FSM anchored to 3 physical waypoints. """
        
        """ 1. Default Initialization (Fail-Safe) """
        action = "HOLD_POSITION"

        """ GUARD 1: Not on runway waypoints """
        if self.current_waypoint not in ["WP1", "WP2", "WP3"]:
            return action

        """ GUARD 2: WP1 Static Hold Check """
        if self.current_waypoint == "WP1":
            if thrust_level < self.MAX_THRUST_N:
                return "HOLD_BRAKES_SPOOL_ENGINES"
            
            """ Thrust is maxed, FSM advances waypoint """
            self.current_waypoint = "WP2"
            return "RELEASE_BRAKES"

        """ GUARD 3: WP2 Acceleration & V1 Verification """
        if self.current_waypoint == "WP2":
            distance_to_wp2 = calculate_spatial_distance(
                current_pos['lat'], current_pos['lon'], current_pos['alt'],
                wp2_pos['lat'], wp2_pos['lon'], wp2_pos['alt']
            )
            
            if distance_to_wp2 >= self.DISTANCE_THRESHOLD_M:
                return "CONTINUE_ACCELERATION"
                
            if velocity_kts < self.V1_SPEED_KTS:
                return "ABORT_TAKEOFF"
                
            """ V1 achieved, FSM preps for rotation """
            self.current_waypoint = "WP3"
            return "CONTINUE_ACCELERATION"

        """ GUARD 4: WP3 Rotation Point Check """
        distance_to_wp3 = calculate_spatial_distance(
            current_pos['lat'], current_pos['lon'], current_pos['alt'],
            wp3_pos['lat'], wp3_pos['lon'], wp3_pos['alt']
        )
        
        if distance_to_wp3 >= self.DISTANCE_THRESHOLD_M and velocity_kts < self.VR_SPEED_KTS:
            return "CONTINUE_ACCELERATION"

        """ HAPPY PATH: Execute Tactical Rotation precisely at WP3 """
        return "EXECUTE_TACTICAL_ROTATION"

    def process_ground_ekf_cycle(self, x_hat, u_vector, dt):
        """ Updates the ground tracking Extended Kalman Filter matrix. """
        
        """ Call the Numba JIT mathematician to process the matrices """
        x_new, P_new = ekf_prediction_step(xp.array(x_hat), xp.array(u_vector), self.P_matrix, self.Q_matrix, float(dt))
        
        """ Store updated covariance back into the class state """
        self.P_matrix = P_new
        
        """ Return state vector converted to 15-decimal precision list for telemetry export """
        if HAS_GPU:
            return xp.round(x_new, 15).get().tolist()
        return xp.round(x_new, 15).tolist()
