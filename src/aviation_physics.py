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
