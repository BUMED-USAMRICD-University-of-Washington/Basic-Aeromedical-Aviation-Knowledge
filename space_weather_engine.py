import telemetry_link
import multiprocessing as mp
# memory_manager.py AFTER telemetry per OSHA!
# Create one shared cache instance for the whole app
shared_cache = DynamicMemoryCache(percentage=0.25)
from dynamic_memory_cache import DynamicMemoryCache
from telemetry_link import time_manager
now = time_manager.get_now()

try:
    import cupy as np  # Attempt to use GPU-accelerated array math
    print("🚀 NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np # Fallback to standard CPU math
    print("⚡ Using CPU (NVIDIA acceleration not detected)")

# --- PRIMARY ENGINE: Space Weather & Kinematics ---
import os
import struct
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord, FK5
import astropy.units as u
from astropy.time import Time

# --- SECONDARY ENGINE DEPENDENCIES ---
import telemetry_link          
import aviation_physics        

try:
    import cupy as np  # Attempt to use GPU-accelerated array math
    print("🚀 NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np # Fallback to standard CPU math
    print("⚡ Using CPU (NVIDIA acceleration not detected)")

class KinematicForceEngine:
    """
    Calculates planetary velocities, rotations, and applies 
    environmental force corrections (J2 oblateness & Space Wind).
    """
    def __init__(self): 
        # Universal Gravitational Constant (m^3 kg^-1 s^-2)
        self.G = 6.67430e-11
    def calculate_future_position():
    # This respects your manual override if you set one!
    now = telemetry_link.time_manager.get_now() 
    future = now + datetime.timedelta(hours=48)
    return future
    def calculate_kinematics_and_forces(
        self,
        pos_t1,
        pos_t2,
        dt,
        planet_mass,
        planet_radius,
        ship_mass,
        ship_area,
        drag_coeff,
        wind_velocity_vec,
        wind_density,
        j2_factor
    ):
        """
        Processes multiple spatial readings to extract velocity and apply corrections.
        """
        # 1. Planetary Velocity Vector
        # v = (r2 - r1) / dt
        velocity_vec = (np.array(pos_t2) - np.array(pos_t1)) / dt
        velocity_mag = np.linalg.norm(velocity_vec)

        # 2. Baseline Spherical Gravity (using pos_t2 as current location)
        r_vec = np.array(pos_t2)
        r_mag = np.linalg.norm(r_vec)
        
        # Fg = G * (m1 * m2) / r^2
        gravity_force_mag = self.G * (planet_mass * ship_mass) / (r_mag**2)
        # Unit vector pointing towards the center of mass
        r_hat = -r_vec / r_mag 
        gravity_vec = gravity_force_mag * r_hat

        # 3. Oblateness Correction (J2 Perturbation)
        # Simplified acceleration correction for a ship at latitude phi
        # Assuming z-axis is polar, latitude approximation: sin(phi) = z / r
        sin_phi = r_vec[2] / r_mag if r_mag != 0 else 0
        j2_accel_factor = -(3/2) * j2_factor * (self.G * planet_mass / (r_mag**2)) * ((planet_radius / r_mag)**2)
        
        a_x = j2_accel_factor * (1 - 5 * sin_phi**2) * (r_vec[0] / r_mag)
        a_y = j2_accel_factor * (1 - 5 * sin_phi**2) * (r_vec[1] / r_mag)
        a_z = j2_accel_factor * (3 - 5 * sin_phi**2) * (r_vec[2] / r_mag)
        
        j2_accel_vec = np.array([a_x, a_y, a_z])
        j2_force_vec = j2_accel_vec * ship_mass

        # 4. Space Wind Drag Force
        # F_wind = 0.5 * rho * Cd * A * |V_rel| * V_rel
        v_rel_vec = np.array(wind_velocity_vec) - velocity_vec
        v_rel_mag = np.linalg.norm(v_rel_vec)
        
        wind_force_vec = 0.5 * wind_density * drag_coeff * ship_area * v_rel_mag * v_rel_vec

        # 5. Net Rectified Force
        total_force_vec = gravity_vec + j2_force_vec + wind_force_vec

        return {
            "orbital_velocity_m_s": velocity_mag,
            "velocity_vector": velocity_vec,
            "pure_gravitational_force_n": gravity_vec,
            "j2_gravitational_correction_n": j2_force_vec,
            "space_wind_force_n": wind_force_vec,
            "total_corrected_force_field_n": total_force_vec
        }


def get_jnow_coordinates(ra_hms: str, dec_dms: str, distance_kpc: float) -> dict:
    """
    Converts static J2000 catalog coordinates to real-time JNow 
    Cartesian vectors based on the current system clock.
    """
    current_utc_time = Time.now()
    
    # Define baseline J2000 coordinate
    j2000_coord = SkyCoord(
        ra=ra_hms, 
        dec=dec_dms, 
        distance=distance_kpc * u.kpc, 
        frame='icrs'
    )
    
    # Precess to exact current date (JNow)
    jnow_coord = j2000_coord.transform_to(FK5(equinox=current_utc_time))
    
    # Extract to Cartesian meters for the physics engine
    jnow_cartesian = jnow_coord.cartesian
    
    return {
        "epoch_utc": current_utc_time.iso,
        "jnow_ra_deg": jnow_coord.ra.deg,
        "jnow_dec_deg": jnow_coord.dec.deg,
        "vector_x_meters": jnow_cartesian.x.to(u.m).value,
        "vector_y_meters": jnow_cartesian.y.to(u.m).value,
        "vector_z_meters": jnow_cartesian.z.to(u.m).value,
        "vector_array": [
            jnow_cartesian.x.to(u.m).value, 
            jnow_cartesian.y.to(u.m).value, 
            jnow_cartesian.z.to(u.m).value
        ]
    }


def execute_tracking_loop():
    """
    Example orchestration showing how to pull sequential JNow readings
    and compute the kinematic force corrections.
    """
    print("--- 🌌 Initializing Advanced Kinematics Tracking ---")
    
    # Target: Andromeda Galaxy (Example target for deep space)
    # In a live scenario, you would pull RA/Dec directly from your Stellarium parser.
    target_ra = '00h42m44.3s'
    target_dec = '+41d16m09s'
    target_dist_kpc = 765.0 
    
    print("Fetching Reading 1 (T1)...")
    reading_1 = get_jnow_coordinates(target_ra, target_dec, target_dist_kpc)
    pos_t1 = reading_1['vector_array']
    
    # Simulate a time delta (e.g., 60 seconds passing between telemetry readings)
    dt_seconds = 60.0 
    
    # In reality, you wait for the tick, but we simulate movement by adjusting the vector
    # slightly for demonstration purposes of the math.
    pos_t2 = [pos_t1[0] + 15000, pos_t1[1] - 8000, pos_t1[2] + 2000] 
    
    # Initialize the Kinematic Engine
    engine = KinematicForceEngine()
    
    # Compute dynamics (Using sample planetary/ship masses)
    results = engine.calculate_kinematics_and_forces(
        pos_t1=pos_t1,
        pos_t2=pos_t2,
        dt=dt_seconds,
        planet_mass=1.5e24,       # Target mass (kg)
        planet_radius=6000e3,     # Target radius (m)
        ship_mass=50000.0,        # Aircraft/Spacecraft mass (kg)
        ship_area=120.0,          # Cross-sectional area (m^2)
        drag_coeff=2.2,           # Drag coefficient
        wind_velocity_vec=[400000, 0, 0], # Solar wind velocity vector (m/s)
        wind_density=1e-12,       # Plasma density (kg/m^3)
        j2_factor=0.00108         # Oblateness harmonic 
    )

    print(f"\n--- JNow Synchronization Epoch: {reading_1['epoch_utc']} ---")
    print(f"JNow RA/Dec: {reading_1['jnow_ra_deg']:.4f}°, {reading_1['jnow_dec_deg']:.4f}°")
    
    print("\n=== KINEMATIC & FORCE TELEMETRY ===")
    print(f"Velocity Vector (m/s): {np.round(results['velocity_vector'], 2)}")
    print(f"Absolute Speed:        {results['orbital_velocity_m_s']:.2f} m/s")
    
    print("\n--- Force Decompositions (Newtons) ---")
    print(f"Baseline Gravity: {np.round(results['pure_gravitational_force_n'], 2)} N")
    print(f"J2 Shape Variance:{np.round(results['j2_gravitational_correction_n'], 2)} N")
    print(f"Space Wind Drag:  {np.round(results['space_wind_force_n'], 2)} N")
    print(f"\nTOTAL NET RECTIFIED FORCE VECTOR: {np.round(results['total_corrected_force_field_n'], 2)} N")


if __name__ == "__main__":
    execute_tracking_loop()
