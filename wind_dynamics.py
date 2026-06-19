import math
try:
    import cupy as xp
    from numba import dummy_njit as njit
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Matrix Allocation Active (Wind Dynamics)")
except ImportError:
    import numpy as xp
    from numba import njit
    HAS_GPU = False
    print("CPU Fallback: Numba Vectorization Active (Wind Dynamics)")
import matplotlib.pyplot as plt
import numba
from numba import njit
import telemetry_link
import aviation_physics
import aircraft_perf
import aviation_telemetry
import aerodynamic_matrix
import sensor_thermodynamics

@njit(fastmath=True)
def compute_3d_wind_shear(u1, v1, w1, u2, v2, w2, dz_meters):
    """ Calculates the absolute shear vector across an altitude delta. """
    
    """ GUARD 1: Prevent division by zero if altitude hasn't changed """
    if abs(dz_meters) < 0.1:
        return 0.0

    """ HAPPY PATH: Calculate gradient (du/dz, dv/dz, dw/dz) """
    du = u2 - u1
    dv = v2 - v1
    dw = w2 - w1
    
    shear_magnitude = math.sqrt((du/dz_meters)**2 + (dv/dz_meters)**2 + (dw/dz_meters)**2)
    return shear_magnitude


@njit(fastmath=True)
def detect_microburst_threat(downdraft_velocity_mps, altitude_agl_meters):
    """ Evaluates atmospheric momentum to predict catastrophic microbursts. """
    
    """ GUARD 1: Safe altitude (Microbursts only lethal near the ground) """
    if altitude_agl_meters > 1000.0:
        return 0.0
        
    """ GUARD 2: Normal air mass (No severe downdraft) """
    if downdraft_velocity_mps > -5.0:
        return 0.0

    """ HAPPY PATH: Severe negative momentum detected """
    """ Calculate kinetic threat multiplier based on proximity to the ground """
    proximity_multiplier = 1000.0 / (altitude_agl_meters + 1.0)
    threat_index = abs(downdraft_velocity_mps) * proximity_multiplier
    
    return threat_index


@njit(fastmath=True)
def calculate_crosswind_component(wind_speed_kts, wind_dir_deg, runway_heading_deg):
    """ Isolates the lateral wind force hitting the vertical stabilizer. """
    
    """ GUARD 1: No wind """
    if wind_speed_kts <= 0.0:
        return 0.0, 0.0
        
    """ HAPPY PATH """
    angular_diff_rad = math.radians(wind_dir_deg - runway_heading_deg)
    
    crosswind_kts = wind_speed_kts * math.sin(angular_diff_rad)
    headwind_kts = wind_speed_kts * math.cos(angular_diff_rad)
    
    return crosswind_kts, headwind_kts

""" ===================================================================== """
""" --- THE ORCHESTRATOR (THE METEOROLOGY MANAGER) --- """
""" ===================================================================== """

class WindDynamicsEngine:
    """ Tracks atmospheric momentum and alerts the FSM to wind shear boundaries. """
    
    def __init__(self):
        """ 15-Decimal Safety Baselines """
        self.SHEAR_WARNING_THRESHOLD = 0.150000000000000
        self.MICROBURST_THREAT_LIMIT = 50.000000000000000
        
        """ Memory buffer for the previous altitude tick to calculate shear delta """
        self.prev_state = None

    def evaluate_wind_shear_threat(self, current_alt_m, current_u, current_v, current_w):
        """ Compares the current millisecond wind vector against the previous tick. """
        
        """ GUARD 1: First tick, initialize memory and exit """
        if self.prev_state is None:
            self.prev_state = (current_alt_m, current_u, current_v, current_w)
            return 0.0, False

        """ HAPPY PATH: Calculate shear using Numba Kernel """
        p_alt, p_u, p_v, p_w = self.prev_state
        dz = current_alt_m - p_alt
        
        shear_value = compute_3d_wind_shear(
            float(p_u), float(p_v), float(p_w),
            float(current_u), float(current_v), float(current_w), float(dz)
        )
        
        """ Update memory for next 120Hz loop """
        self.prev_state = (current_alt_m, current_u, current_v, current_w)
        
        """ GUARD 2: Shear exceeds structural or aerodynamic safety margins """
        if shear_value > self.SHEAR_WARNING_THRESHOLD:
            return round(float(shear_value), 15), True
            
        return round(float(shear_value), 15), False

    def process_live_wind_telemetry(self, ship_altitude_agl_m, runway_heading_deg, wind_payload):
        """ Master cycle. Ingests localized anemometer or NOAA grid data. """
        
        w_speed = float(wind_payload.get('speed_kts', 0.0))
        w_dir = float(wind_payload.get('direction_deg', 0.0))
        w_down = float(wind_payload.get('downdraft_mps', 0.0))
        
        """ 1. Calculate physical components hitting the airframe """
        cross_kts, head_kts = calculate_crosswind_component(
            float(w_speed), float(w_dir), float(runway_heading_deg)
        )
        
        """ 2. Evaluate catastrophic microburst momentum """
        microburst_index = detect_microburst_threat(
            float(w_down), float(ship_altitude_agl_m)
        )
        
        is_microburst = False
        if microburst_index > self.MICROBURST_THREAT_LIMIT:
            is_microburst = True
            
        """ 3. Format 15-Decimal Payload for the FSM """
        payload = {
            "crosswind_kts": round(float(cross_kts), 15),
            "headwind_kts": round(float(head_kts), 15),
            "microburst_detected": is_microburst,
            "microburst_threat_index": round(float(microburst_index), 15)
        }
        
        """ Broadcast to Flight Controls so the PID loop can instantly apply rudder pressure """
        telemetry_link.update_global_state("environment", "wind_dynamics", payload)
        
        return payload

@njit(fastmath=True)
def calculate_density_and_cooling(temp_c, wind_mph, relative_humidity=0.50):
    """
    Solves the combined gas density and convective wind cooling equations
    for atmospheric weather analysis.
    """
    T_kelvin = temp_c + 273.15
    P_total = 101325.0
    es = 611.2 * np.exp((17.67 * temp_c) / (temp_c + 243.5))
    Pv = es * relative_humidity
    Pd = P_total - Pv
    R_d = 287.05
    R_v = 461.495
    air_density = (Pd / (R_d * T_kelvin)) + (Pv / (R_v * T_kelvin))
    T_fahrenheit = (temp_c * 9.0/5.0) + 32.0
    if T_fahrenheit <= 50.0 and wind_mph >= 3.0:
        v_factor = wind_mph ** 0.16
        wind_chill_f = 35.74 + (0.6215 * T_fahrenheit) - (35.75 * v_factor) + (0.4275 * T_fahrenheit * v_factor)
        wind_chill_c = (wind_chill_f - 32.0) * 5.0/9.0
        cooling_delta = temp_c - wind_chill_c
    else:
        wind_chill_c = temp_c
        cooling_delta = 0.0
    return air_density, wind_chill_c, cooling_delta
    
@njit(fastmath=True)
def run_wind_layer(telemetry_override=None):
    """
    Main orchestration function. Extracts live telemetry, runs the high-performance
    physics simulation, and reports the findings directly to the Boeing JSON payload.
    """
    print("Running Wind Dynamics Matrix...")
    temp = 4.0
    wind = 15.0
    rh = 0.50
    if telemetry_override:
        temp = telemetry_override.get('temp_c', temp)
        wind = telemetry_override.get('wind_mph', wind)
        raw_rh = telemetry_override.get('rh_pct', rh * 100.0)
        rh = raw_rh / 100.0 if raw_rh > 1.0 else raw_rh
    density, chill, delta = calculate_density_and_cooling(
        temp_c=temp, 
        wind_mph=wind, 
        relative_humidity=rh
    )
    payload = {
        "base_temp_c": temp,
        "wind_speed_mph": wind,
        "relative_humidity": rh,
        "air_density_kg_m3": round(float(density), 4),
        "wind_chill_c": round(float(chill), 2),
        "convective_cooling_delta_c": round(float(delta), 2)
    }
    telemetry_link.update_global_state("dynamics", "wind_matrix", payload)
    print("Wind dynamics calculations reported to global state.")
    return payload
    
if __name__ == "__main__":
    print("================================================================")
    print("         NWS WIND DENSITY & COOLING INDEX SOLVER                ")
    print("================================================================")
    test_temp_c = 4.0
    wind_scenarios = [5.0, 15.0, 35.0]
    print(f"Baseline Temperature: {test_temp_c}°C | Relative Humidity: 50%\n")
    for wind in wind_scenarios:
        density, chill, delta = calculate_density_and_cooling(test_temp_c, wind)
        print(f"💨 Wind Speed Velocity: {wind:<4} mph")
        print(f"   -> Calculated Air Density:   {density:.4f} kg/m³")
        print(f"   -> Resulting Wind Chill:     {chill:.2f}°C")
        print(f"   -> Convective Degree Drop:   -{delta:.2f}°C variation")
        print("-" * 55)
