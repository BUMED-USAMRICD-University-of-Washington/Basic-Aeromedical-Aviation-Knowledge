import numpy as np
from numba import njit

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
