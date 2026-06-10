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

    """ Store in memory cache before returning """
    shared_cache.add_to_cache(cache_key, final_array)
    return final_array
