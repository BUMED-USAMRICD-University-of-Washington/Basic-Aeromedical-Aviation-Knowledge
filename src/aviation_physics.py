import numpy as np
from numba import njit

@njit
def compute_jit_3d_and_fuel_metrics(current_state, horizontal_waypoint, target_altitude, performance_limits, wind_vector, fuel_state):
    """
    Unified 3D Physics and Fuel Endurance Processing Loop.
    Executes at 1000Hz with zero allocation memory overhead.
    
    Parameters:
        current_state (float64[:]): [lat, lon, altitude_ft, tas_knots, heading_deg]
        horizontal_waypoint (float64[:]): [target_lat, target_lon]
        target_altitude (float64): Sliced holding altitude (feet)
        performance_limits (float64[:]): [max_climb_fpm, max_descent_fpm, optimal_glide_deg, base_burn_pph]
        wind_vector (float64[:]): [wind_direction_deg, wind_speed_kts]
        fuel_state (float64[:]): [current_fuel_lbs, diversion_fuel_lbs, current_bank_deg]
        
    Returns:
        float64[:]: Unified output telemetry bus array:
                    [target_vs_fpm, target_hdg_deg, crosswind_kts, fuel_flow_pph, bingo_threshold_lbs, endurance_mins]
    """
    # 1. Extract Core Variables
    cur_lat, cur_lon, cur_alt, cur_tas, _ = current_state[0], current_state[1], current_state[2], current_state[3], current_state[4]
    target_lat, target_lon = horizontal_waypoint[0], horizontal_waypoint[1]
    wind_dir, wind_spd = wind_vector[0], wind_vector[1]
    max_climb, max_descent, optimal_glide, base_burn_pph = performance_limits[0], performance_limits[1], performance_limits[2], performance_limits[3]
    current_fuel, diversion_fuel, bank_deg = fuel_state[0], fuel_state[1], fuel_state[2]

    # 2. Vertical Core Tracking (Z-Axis)
    alt_error = target_altitude - cur_alt
    target_vs = 0.0
    if abs(alt_error) >= 10.0:
        if alt_error < 0:
            tas_fpm = cur_tas * 101.269
            calculated_descent = tas_fpm * np.tan(np.radians(optimal_glide))
            target_vs = -min(calculated_descent, max_descent)
        else:
            target_vs = min(alt_error * 2.5, max_climb)

    # 3. Horizontal & Crab Tracking (X/Y-Axis)
    error_lat = target_lat - cur_lat
    error_lon = (target_lon - cur_lon) * np.cos(np.radians(cur_lat))
    true_course = np.degrees(np.arctan2(error_lon, error_lat)) % 360.0
    
    crosswind_kts = wind_spd * np.sin(np.radians(abs(wind_dir - true_course)))
    crab_angle = np.degrees(np.arcsin(crosswind_kts / cur_tas)) if cur_tas > abs(crosswind_kts) and cur_tas > 10.0 else 0.0
    
    wind_relative = (wind_dir - true_course) % 360.0
    target_hdg = (true_course - crab_angle) % 360.0 if wind_relative > 180.0 else (true_course + crab_angle) % 360.0

    # 4. Aerodynamic Propulsion & Fuel Depletion Math
    alt_modifier = max(0.5, 1.0 - (0.03 * (cur_alt / 1000.0)))
    bank_modifier = 1.0 / max(0.5, np.cos(np.radians(bank_deg)))
    fuel_flow_pph = base_burn_pph * alt_modifier * bank_modifier
    
    faa_45min_reserve = (fuel_flow_pph / 60.0) * 45.0
    bingo_threshold = diversion_fuel + faa_45min_reserve
    
    usable_fuel = current_fuel - bingo_threshold
    endurance_mins = max(0.0, usable_fuel / (fuel_flow_pph / 60.0)) if usable_fuel > 0 else 0.0

    # 5. Pack Outputs into flat continuous block
    out = np.empty(6, dtype=np.float64)
    out[0], out[1], out[2], out[3], out[4], out[5] = target_vs, target_hdg, crosswind_kts, fuel_flow_pph, bingo_threshold, endurance_mins
    return out


@njit
def compute_jit_3d_unified_guidance(current_state, horizontal_waypoint, target_altitude, performance_limits, wind_vector):
    """
    Unified 3D Autopilot Guidance Engine. Compiled via Numba for native microsecond execution.
    
    Parameters:
        current_state (float64[:]): [current_lat, current_lon, current_alt_ft, current_tas_kts, current_heading_deg]
        horizontal_waypoint (float64[:]): [target_lat, target_lon]
        target_altitude (float64): Sliced FAA legal holding level (feet)
        performance_limits (float64[:]): [max_climb_rate_fpm, max_descent_rate_fpm, optimal_glidepath_deg]
        wind_vector (float64[:]): [wind_direction_deg, wind_speed_kts]
        
    Returns:
        float64[:]: Unified output guidance vector [target_vertical_speed_fpm, commanded_crab_heading_deg, crosswind_component_kts]
    """
    # Unpack aircraft state variables
    cur_lat = current_state[0]
    cur_lon = current_state[1]
    cur_alt = current_state[2]
    cur_tas = current_state[3]
    
    target_lat = horizontal_waypoint[0]
    target_lon = horizontal_waypoint[1]
    
    wind_dir = wind_vector[0]
    wind_spd = wind_vector[1]

    # ==========================================
    # 1. VERTICAL PLANE CALCULATIONS (Z-AXIS)
    # ==========================================
    max_climb_rate = performance_limits[0]
    max_descent_rate = performance_limits[1]
    optimal_glidepath_deg = performance_limits[2]
    
    altitude_error = target_altitude - cur_alt
    target_vs = 0.0
    
    if abs(altitude_error) >= 10.0:  # 10-ft deadband filter
        if altitude_error < 0:  # Descent Math
            tas_fpm = cur_tas * 101.269
            gamma_rad = np.radians(optimal_glidepath_deg)
            calculated_descent_rate = tas_fpm * np.tan(gamma_rad)
            target_vs = -min(calculated_descent_rate, max_descent_rate)
        else:  # Climb Math
            proportional_climb = altitude_error * 2.5
            target_vs = min(proportional_climb, max_climb_rate)

    # ==========================================
    # 2. HORIZONTAL PLANE & WIND VECTOR MATH (X/Y-AXIS)
    # ==========================================
    # Calculate geometric track tracking direction to target node (True Course)
    # Simple mercator approximation for terminal environment scaling
    error_lat = target_lat - cur_lat
    # Scaling longitude tracking dynamically based on current lat position
    error_lon = (target_lon - cur_lon) * np.cos(np.radians(cur_lat))
    
    true_course_deg = np.degrees(np.arctan2(error_lon, error_lat)) % 360.0
    
    # Calculate angular wind offset intercept relative to target path
    wind_angle_rad = np.radians(abs(wind_dir - true_course_deg))
    
    # Isolate crosswind component velocity
    crosswind_kts = wind_spd * np.sin(wind_angle_rad)
    
    # Trigonometric Crab Angle Correction (WCA)
    # Security bounds check to prevent arcsin domain crashing if crosswind exceeds aircraft TAS
    if cur_tas > abs(crosswind_kts) and cur_tas > 10.0:
        crab_angle_deg = np.degrees(np.arcsin(crosswind_kts / cur_tas))
    else:
        crab_angle_deg = 0.0  # Safe recovery state if aircraft is practically static

    # Apply directional sign to crab adjustment depending on wind source orientation
    # Determine if wind is pushing from left or right side of true track
    wind_relative = (wind_dir - true_course_deg) % 360.0
    if wind_relative > 180.0:
        commanded_heading = (true_course_deg - crab_angle_deg) % 360.0
    else:
        commanded_heading = (true_course_deg + crab_angle_deg) % 360.0

    # Build and export continuous unified output vector memory array
    output_vector = np.empty(3, dtype=np.float64)
    output_vector[0] = target_vs
    output_vector[1] = commanded_heading
    output_vector[2] = crosswind_kts
    
    return output_vector
@njit
def compute_next_guidance_vector(current_state, waypoint_array):
    """
    JIT-accelerated guidance loop. Computes error vectors at 1000Hz.
    waypoint_array: Nx2 array of [[lat, lon], [lat, lon], ...]
    current_state: 1D array [lat, lon, airspeed, heading]
    """
    cur_lat = current_state[0]
    cur_lon = current_state[1]
    current_alt = current_state[2]
    current_tas = current_state[3]
    
    max_climb_rate = performance_limits[0]
    max_descent_rate = performance_limits[1]
    optimal_glidepath_deg = performance_limits[2]
    
    # 1. Compute direct raw vertical tracking error
    altitude_error = target_altitude - current_alt
    
    # 2. Prevent chattering: Introduce a small 10-foot vertical deadband zone
    if abs(altitude_error) < 10.0:
        return 0.0, altitude_error
        
    # 3. Handle descent path aerodynamics using glideslope trigonometry
    if altitude_error < 0:
        # Convert true airspeed knots to feet per minute ground-run approximation
        tas_fpm = current_tas * 101.269
        
        # Calculate standard aerodynamic glideslope descent target rate
        gamma_rad = np.radians(optimal_glidepath_deg)
        calculated_descent_rate = tas_fpm * np.tan(gamma_rad)
        
        # Enforce structural airframe envelope constraints (ensure value stays negative)
        target_vs = -min(calculated_descent_rate, max_descent_rate)
        
    # 4. Handle climb performance
    else:
        # Scale climb aggressiveness proportionally to the altitude error gap
        proportional_climb = altitude_error * 2.5
        target_vs = min(proportional_climb, max_climb_rate)
        
    return target_vs, altitude_error        
    # Simple array lookup loop optimized by Numba
    num_points = waypoint_array.shape[0]
    target_idx = 0
    
    # Distance tracking to find the active waypoint step
    for i in range(num_points):
        d_lat = waypoint_array[i, 0] - cur_lat
        d_lon = waypoint_array[i, 1] - cur_lon
        dist = np.sqrt(d_lat**2 + d_lon**2)
        
        if dist > 0.005:  # Close enough to sequence to next point
            target_idx = i
            break
            
    target_lat = waypoint_array[target_idx, 0]
    target_lon = waypoint_array[target_idx, 1]
    
    # Compute error components
    error_lat = target_lat - cur_lat
    error_lon = target_lon - cur_lon
    desired_heading = np.degrees(np.arctan2(error_lon, error_lat)) % 360.0
    
    return desired_heading, target_idx
