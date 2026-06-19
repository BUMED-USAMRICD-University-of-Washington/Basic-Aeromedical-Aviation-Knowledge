import numpy as np
from numba import njit

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
