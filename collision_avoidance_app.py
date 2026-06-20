""" collision_avoidance_app.py """
""" NextGen ACAS X & ADS-B Cooperative Collision Avoidance Engine """
""" Optimized: Else-Less Guard Clauses | 15-Decimal Precision | Numba Kernels """
import time
import math
import telemetry_link
from intent_engine import IntruderIntentAnalyst
from pathlib import Path
from terrain_manager import AviationTerrainEngine

""" --- HARDWARE ABSTRACTION LAYER (HAL) --- """
try:
    import cupy as xp
    from numba import dummy_njit as njit
    HAS_GPU = True
except ImportError:
    import numpy as xp
    from numba import njit
    HAS_GPU = False

# Point this relative to your structural source deployment framework location
# Targets: E:\GitHub\Basic-Aviation-Knowledge\src\earth\h5
EARTH_H5_ROOT = Path(__file__).resolve().parent / "earth" / "h5"

class GroundCollisionAvoidanceSystem:
    """
    Flight deck advisory computer layer. Matches vehicle telemetry metrics 
    against high-performance H5 digital elevation grids.
    """
    def __init__(self, data_path: Path):
        print("[GCAS INIT] Coupling system threads with terrain database core...")
        self.terrain_engine = AviationTerrainEngine(str(data_path))
        
        # Safety margin envelopes (In Meters)
        self.CAUTION_AGL_THRESHOLD = 300.0  # Alert below ~1,000 feet Above Ground Level
        self.WARNING_AGL_THRESHOLD = 150.0  # Critical threat below ~500 feet Above Ground Level

    def monitor_flight_telemetry(self, lat: float, lon: float, altitude_msl: float):
        """
        Primary execution node. Call this parameter loop inside your vehicle's core flight updates.
        Returns state tracking maps alongside clearance indicators.
        """
        # 1. Update terrain tile layer allocations automatically
        self.terrain_engine.update_aircraft_position(lat, lon)
        
        # 2. Extract precise ground point elevation bounds
        ground_elevation = self.terrain_engine.get_ground_elevation(lat, lon)
        
        # 3. Compute structural separation properties
        altitude_agl = altitude_msl - ground_elevation
        
        # 4. Process critical separation assessment states
        if altitude_agl <= self.WARNING_AGL_THRESHOLD:
            status = "CRITICAL PULL UP WARNING"
            alert_level = 2
        elif altitude_agl <= self.CAUTION_AGL_THRESHOLD:
            status = "TERRAIN PROXIMITY CAUTION"
            alert_level = 1
        else:
            status = "NORMAL SEPARATION OPERATIONAL"
            alert_level = 0
            
        return {
            "status": status,
            "alert_level": alert_level,
            "ground_m": round(ground_elevation, 1),
            "clearance_m": round(altitude_agl, 1)
        }

# =====================================================================
# SYSTEM VERIFICATION WORKER
# =====================================================================
if __name__ == "__main__":
    # Instantiate simulation environment lines
    gcas_computer = GroundCollisionAvoidanceSystem(EARTH_H5_ROOT)
    
    # Mock Flight telemetry tracking a descent vector into mountainous terrain boundaries
    simulated_telemetry_stream = [
        {"lat": 47.606, "lon": -122.332, "alt_msl": 600.0},  # Transitioning past coastlines
        {"lat": 47.450, "lon": -121.800, "alt_msl": 500.0},  # Entering mountain approaches
        {"lat": 47.442, "lon": -121.750, "alt_msl": 420.0}   # Severe risk proximity threat point
    ]
    
    print("\n[SIMULATION START] Beginning automated flight loop tracking processing passes...")
    for index, packet in enumerate(simulated_telemetry_stream, start=1):
        telemetry = gcas_computer.monitor_flight_telemetry(
            packet["lat"], packet["lon"], packet["alt_msl"]
        )
        
        print(f"\n[FRAME {index:02d}] Position: ({packet['lat']}, {packet['lon']}) | Aircraft Altitude: {packet['alt_msl']}m")
        print(f"   Terrain Elevation: {telemetry['ground_m']}m | Vertical Clearance AGL: {telemetry['clearance_m']}m")
        print(f"   System Status Advisory Flags: [{telemetry['status']}]")
        
        time.sleep(0.5)

""" ===================================================================== """
""" --- PURE MATH KERNELS (THE AVIATION MATHEMATICIANS) --- """
""" ===================================================================== """

@njit(fastmath=True)
def imm_predict_and_update(x_hat, z_meas, dt, omega):
    """ Interacting Multiple Model (IMM) tracking filter. """
    if dt <= 0.0: return x_hat

    x_pred = x_hat[0] + (x_hat[3] * dt)
    y_pred = x_hat[1] + (x_hat[4] * dt)
    z_pred = x_hat[2] + (x_hat[5] * dt)
    
    x_new = x_pred + omega * (z_meas[0] - x_pred)
    y_new = y_pred + omega * (z_meas[1] - y_pred)
    z_new = z_pred + omega * (z_meas[2] - z_pred)

    vx_new = (x_new - x_hat[0]) / dt
    vy_new = (y_new - x_hat[1]) / dt
    vz_new = (z_new - x_hat[2]) / dt

    return xp.array([x_new, y_new, z_new, vx_new, vy_new, vz_new])

@njit(fastmath=True)
def evaluate_cooperative_bellman_resolution(own_alt, target_alt, own_vz, target_vz, tti, cooperative_mode):
    """ ACAS X Markov Decision Process (MDP) Cost Matrix. """
    if tti > 45.0: return 0.0, 0.0
        
    rel_alt = target_alt - own_alt
    cost_maintain = 100.0 / (abs(rel_alt) + 1.0)
    
    projected_rel_alt_climb = (target_alt + target_vz * tti) - (own_alt + 7.62 * tti)
    cost_climb = 100.0 / (abs(projected_rel_alt_climb) + 1.0)
    if cooperative_mode == 1.0: cost_climb = 999999.0
        
    projected_rel_alt_dive = (target_alt + target_vz * tti) - (own_alt - 7.62 * tti)
    cost_dive = 100.0 / (abs(projected_rel_alt_dive) + 1.0)
    if cooperative_mode == -1.0: cost_dive = 999999.0

    best_cost = cost_maintain
    best_action = 0.0
    
    if cost_climb < best_cost:
        best_cost = cost_climb
        best_action = 1.0 
    if cost_dive < best_cost:
        best_cost = cost_dive
        best_action = -1.0
        
    return best_action, best_cost

@njit(fastmath=True)
def compute_intent_correlation(vx_int, vy_int, vz_int, ux_track, uy_track, uz_track):
    """ ADS-B Route Tracking (Cosine Similarity). """
    dot_product = (vx_int * ux_track) + (vy_int * uy_track) + (vz_int * uz_track)
    mag_v = math.sqrt(vx_int**2 + vy_int**2 + vz_int**2)
    mag_u = math.sqrt(ux_track**2 + uy_track**2 + uz_track**2)
    
    if mag_v <= 0.0 or mag_u <= 0.0: return 0.0
    correlation = dot_product / (mag_v * mag_u)
    if correlation > 1.0: return 1.0
    if correlation < -1.0: return -1.0
    return correlation

@njit(fastmath=True)
def compute_closing_metrics(sx, sy, sz, vx, vy, vz, tx, ty, tz, tvx, tvy, tvz):
    """ Calculates Absolute Distance and Closing Time-To-Impact (TTI). """
    dx = tx - sx
    dy = ty - sy
    dz = tz - sz
    distance = math.sqrt(dx**2 + dy**2 + dz**2)
    
    rx = vx - tvx
    ry = vy - tvy
    rz = vz - tvz
    closing_vel = math.sqrt(rx**2 + ry**2 + rz**2)
    
    if closing_vel <= 0.0: return distance, 999999.0
    tti = distance / closing_vel
    return distance, tti


""" ===================================================================== """
""" --- THE ORCHESTRATOR (THE RADAR MANAGER) --- """
""" ===================================================================== """

class CollisionAvoidanceSystem:
    def __init__(self):
        self.BASE_TTI_THRESHOLD_SEC = 45.000000000000000
        self.BASE_BUBBLE_RADIUS_M = 5000.000000000000000
        self.INTENT_CORRELATION_LIMIT = 0.990000000000000
        self.FILTER_OMEGA = 0.020000000000000
        
        """ The Distributed Engine Link """
        self.intent_analyst = IntruderIntentAnalyst(dt=0.1)

    def extract_kinematic_features(self, vx, vy, vz):
        """ Transforms 3D velocity vectors into aviation formats for the intent engine. """
        gs_mps = math.sqrt(vx**2 + vy**2)
        gs_kts = gs_mps / 0.514444
        track_deg = math.degrees(math.atan2(vx, vy)) % 360.0
        baro_rate_fpm = vz / (0.3048 / 60.0)
        return gs_kts, track_deg, baro_rate_fpm

    def determine_bellman_resolution(self, ship_state, target_state, tti, dt):
        """ Invokes the ACAS X Cooperative MDP Matrix. """
        x_hat_target = xp.array(target_state['imm_state'])
        z_meas = xp.array(target_state['raw_pos'])
        
        smoothed_target = imm_predict_and_update(
            x_hat_target, z_meas, float(dt), self.FILTER_OMEGA
        )
        
        target_vz = smoothed_target[5]
        cooperative_flag = 0.0
        
        if target_vz > 2.0: cooperative_flag = 1.0
        if target_vz < -2.0: cooperative_flag = -1.0
        
        action_id, cost = evaluate_cooperative_bellman_resolution(
            float(ship_state['pos'][2]), float(smoothed_target[2]),
            float(ship_state['vel'][2]), float(target_vz),
            float(tti), cooperative_flag
        )
        
        maneuver_dict = {
            "0.0": "MAINTAIN_TRAJECTORY",
            "1.0": "CLIMB_RESOLUTION",
            "-1.0": "DIVE_RESOLUTION"
        }
        
        return maneuver_dict.get(str(action_id), "MAINTAIN_TRAJECTORY"), round(float(cost), 15), smoothed_target

    def process_radar_sweep(self, ship_state, intruders_list, active_runway_vec, dt=0.1):
        """ Master Avoidance Loop. Executes Else-less sequence. """
        critical_threats = []
        
        for target in intruders_list:
            
            """ 1. Extract distances """
            dist, tti = compute_closing_metrics(
                float(ship_state['pos'][0]), float(ship_state['pos'][1]), float(ship_state['pos'][2]),
                float(ship_state['vel'][0]), float(ship_state['vel'][1]), float(ship_state['vel'][2]),
                float(target['raw_pos'][0]), float(target['raw_pos'][1]), float(target['raw_pos'][2]),
                float(target['raw_vel'][0]), float(target['raw_vel'][1]), float(target['raw_vel'][2])
            )
            
            """ GUARD 1: Target is outside visual tracking radius """
            if dist > (self.BASE_BUBBLE_RADIUS_M * 2.0):
                continue
                
            """ 2. Determine geometric route intent (Cosine Math) """
            route_correlation = compute_intent_correlation(
                float(target['raw_vel'][0]), float(target['raw_vel'][1]), float(target['raw_vel'][2]),
                float(active_runway_vec[0]), float(active_runway_vec[1]), float(active_runway_vec[2])
            )
            
            """ GUARD 2: Target is safely on ATC corridor """
            if route_correlation > self.INTENT_CORRELATION_LIMIT:
                continue

            """ 3. Determine dynamic behavior intent (via Dynamic Import) """
            gs_kts, track_deg, baro_fpm = self.extract_kinematic_features(
                float(target['raw_vel'][0]), float(target['raw_vel'][1]), float(target['raw_vel'][2])
            )
            target_id = target.get("id", "UNKNOWN")
            behavior_intent, lat_g, vert_g = self.intent_analyst.diagnose_behavior_profile(
                target_id, gs_kts, track_deg, baro_fpm
            )
                
            """ GUARD 3: Target is inside danger envelope """
            if tti < self.BASE_TTI_THRESHOLD_SEC:
                
                resolution, cost, new_imm_state = self.determine_bellman_resolution(
                    ship_state, target, tti, dt
                )
                
                threat_payload = {
                    "target_id": target_id,
                    "distance_m": round(float(dist), 15),
                    "time_to_impact_sec": round(float(tti), 15),
                    "dynamic_behavior": behavior_intent,
                    "acas_resolution": resolution,
                    "resolution_cost": cost
                }
                
                critical_threats.append(threat_payload)
                telemetry_link.update_global_state("threat_management", "active_alert", threat_payload)

        return critical_threats
