import telemetry_link
from dynamic_memory_cache import DynamicMemoryCache
from telemetry_link import time_manager
shared_cache = DynamicMemoryCache(percentage=0.45)
import multiprocessing as mp
import numpy as np
from numba import njit
@njit(fastmath=True) # fastmath enables hardware-level floating point optimizations
import pandas as pd
import matplotlib.pyplot as plt
import math
import aviation_physics
import aviation_telemetry
import aircraft_perf
import sensor_thermodynamics
import aerodynamic_matrix
import streamlit as st
""" aviation_physics.py """
""" Enterprise Batched Atmospheric Engine """
""" Optimized: Else-Less Guard Clauses | CUDA/NumPy HAL | Numba | Memory Caching """
""" --- HARDWARE ABSTRACTION LAYER (HAL) --- """
try:
    import cupy as xp
    from numba import dummy_njit as njit
    """ CuPy handles JIT, mock Numba """
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Array Batching Active (Aviation Physics)")
except ImportError:
    """ CPU JIT Compilation """
    HAS_GPU = False
    print("CPU Fallback: Numba Vectorization Active (Aviation Physics)")

def compute_atmospheric_density(altitude_ft, local_baro_hpa):
    """ Else-less computation of air density using the International Standard Atmosphere (ISA). """
    
    """ 1. Default Initializations """
    pressure_hpa = local_baro_hpa
    rho_sea_level = 1.225
    
    """ GUARD 1: Flight Level Transition (Class A Airspace Standard) """
    if altitude_ft >= 18000.0:
        pressure_hpa = 1013.25

    """ GUARD 2: Extreme Altitude Drop-off (Karman Line Approach) """
    if altitude_ft > 100000.0:
        return 0.0

    """ HAPPY PATH: Standard Aerodynamic Calculation """
    """ Scale density via exponential altitude decay and pressure ratio """
    density_ratio = pressure_hpa / 1013.25
    altitude_m = altitude_ft * 0.3048
    
    """ Approximation of ISA density formula """
    current_rho = rho_sea_level * density_ratio * xp.exp(-altitude_m / 8500.0)
    
    return current_rho


def get_dynamic_pressure_grid(altitude_ft_arr, local_baro_hpa_arr, indicated_airspeed_kts_arr):
    """ Batched computation of dynamic pressure (q = 0.5 * rho * v^2). """
    """ Utilizes caching to prevent recalculating static mission waypoints. """

    """ GUARD 1: Check Memory Cache first (O(1) lookup) """
    cache_key = f"q_grid_{hash(str(altitude_ft_arr[:5]))}"
    cached_result = shared_cache.check_cache(cache_key)
    if cached_result is not None:
        return cached_result

    """ HAPPY PATH: Compute Grid via HAL """
    alt = xp.array(altitude_ft_arr, dtype=xp.float64)
    baro = xp.array(local_baro_hpa_arr, dtype=xp.float64)
    ias_kts = xp.array(indicated_airspeed_kts_arr, dtype=xp.float64)
    
    """ Vectorized application of the density function """
    rho_array = compute_atmospheric_density(alt, baro)
    
    velocity_mps = ias_kts * 0.514444
    dynamic_pressure_arr = 0.5 * rho_array * (velocity_mps ** 2)
    
    """ Return 15-decimal floats """
    if HAS_GPU:
        final_array = xp.round(dynamic_pressure_arr, 15).get().tolist()
    if not HAS_GPU:
        final_array = xp.round(dynamic_pressure_arr, 15).tolist()

def calculate_ground_effect_ratio(height_ft, wingspan_ft):
    """ Else-less Ground Effect (Induced Drag Reduction) """
    
    """ GUARD 1: Prevent division by zero or invalid geometry """
    if wingspan_ft <= 0.0:
        return 1.0

    """ GUARD 2: Aircraft is out of ground effect (typically > 1 wingspan) """
    """ Bypasses all complex math when mid-air """
    if height_ft >= wingspan_ft:
        return 1.0

    """ HAPPY PATH: Calculate aerodynamic reduction ratio """
    h_b_ratio = height_ft / wingspan_ft
    ratio = (33.0 * (h_b_ratio ** 2)) / (1.0 + 33.0 * (h_b_ratio ** 2))
    
    return ratio

    import math

def calculate_crab_angle(wind_speed_kts, wind_dir_deg, runway_heading_deg, tas_kts):
    """ Else-less Wind Correction Angle (WCA) """

    """ GUARD 1: Aircraft is stationary (Prevents division by zero) """
    if tas_kts <= 0.0:
        return 0.0, 0.0

    """ HAPPY PATH: Calculate Crosswind Component """
    alpha_rad = math.radians(wind_dir_deg - runway_heading_deg)
    v_crosswind = wind_speed_kts * math.sin(alpha_rad)

    """ GUARD 2: Crosswind exceeds True Airspeed """
    """ If the wind is blowing faster than the jet can fly, it is physically impossible to crab. """
    if tas_kts <= abs(v_crosswind):
        return 0.0, v_crosswind

    """ HAPPY PATH: Calculate Final Crab Angle (Theta) """
    theta_rad = math.asin(v_crosswind / tas_kts)
    theta_deg = math.degrees(theta_rad)

    return theta_deg, v_crosswind

    import math

def compute_isa_temperature(altitude_ft):
    """ ISA Temperature Model (Celsius) """
    
    """ GUARD 1: Stratosphere Tropopause clamp """
    """ Above 36,089 ft, temperature stops dropping and holds at -56.5 C """
    if altitude_ft >= 36089.0:
        return -56.5
        
    """ HAPPY PATH: Standard lapse rate (-1.98 C per 1000 ft) """
    return 15.0 - (1.98 * (altitude_ft / 1000.0))

def calculate_mach_number(tas_kts, temp_c):
    """ Calculates Mach Number based on local speed of sound """
    
    """ GUARD 1: Aircraft is stationary """
    if tas_kts <= 0.0: 
        return 0.0
        
    """ HAPPY PATH: a = 38.945 * sqrt(Temp_Kelvin) in knots """
    temp_k = temp_c + 273.15
    speed_of_sound_kts = 38.945 * math.sqrt(temp_k)
    
    return tas_kts / speed_of_sound_kts

def calculate_ground_acceleration(thrust_n, drag_n, weight_n, friction_coef):
    """ Tactical Takeoff Roll Acceleration (dV/dt) """
    
    """ GUARD 1: Airborne or Invalid Weight """
    if weight_n <= 0.0: 
        return 0.0
        
    """ HAPPY PATH: dV/dt = g * ((T - D - Fr) / W) """
    friction_force = friction_coef * weight_n
    net_force = thrust_n - drag_n - friction_force
    
    """ GUARD 2: Brakes/Friction holding aircraft completely still """
    if net_force <= 0.0: 
        return 0.0
        
    acceleration_mps2 = 9.80665 * (net_force / weight_n)
    return acceleration_mps2

def calculate_tactical_climb_angle(thrust_n, drag_n, weight_n):
    """ Steep tactical departure climb angle to clear threat rings """
    
    """ GUARD 1: Drag exceeds thrust, climb is physically impossible """
    if drag_n >= thrust_n: 
        return 0.0
        
    """ HAPPY PATH: gamma = arcsin((T - D) / W) """
    excess_thrust = thrust_n - drag_n
    
    """ GUARD 2: Vertical climb maximum cap (T/W ratio > 1) """
    if excess_thrust >= weight_n: 
        return 90.0
        
    angle_rad = math.asin(excess_thrust / weight_n)
    return math.degrees(angle_rad)

@njit(fastmath=True)
def calculate_accelerated_stall_speed(v_s0_kts, bank_angle_deg):
    """ Tactical Bank Accelerated Stall Limit (V_s,acc) """
    
    """ GUARD 1: Pure vertical bank is physically impossible to maintain level flight """
    if bank_angle_deg >= 90.0 or bank_angle_deg <= -90.0: 
        return 9999.0
        
    """ HAPPY PATH: Vs_acc = Vs0 * sqrt(1 / cos(bank)) """
    bank_rad = math.radians(abs(bank_angle_deg))
    load_factor = 1.0 / math.cos(bank_rad)
    
    return v_s0_kts * math.sqrt(load_factor)
    
    """ Store in memory cache before returning """
    shared_cache.add_to_cache(cache_key, final_array)
    return final_array
