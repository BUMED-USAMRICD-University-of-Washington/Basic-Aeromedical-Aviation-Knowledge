import telemetry_link
import datetime
from telemetry_link import time_manager
now = time_manager.get_now()
import matplotlib.pyplot as plt
import telemetry_link
import aviation_physics
import aviation_telemetry
import aircraft_perf
import sensor_thermodynamics
import aerodynamic_matrix
import streamlit as st
try:
    import cupy as xp
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Array Batching Active (Performance)")
except ImportError:
    import numpy as xp
    HAS_GPU = False
    print("CPU Fallback: Standard Vectorization Active (Performance)")
""" MISSING KERNEL: cloud_temperature_drop.py """
from numba import njit
import math

@njit(fastmath=True)
def compute_adiabatic_temperature_drop(t_surface_k, altitude_m, is_saturated):
    """ Calculates temperature drop due to atmospheric lifting (Lapse Rate). """
    
    """ GUARD 1: Below sea level or negative Kelvin """
    if altitude_m <= 0.0 or t_surface_k <= 0.0:
        return t_surface_k
        
    """ Constants for lapse rates (Kelvin drop per meter) """
    DRY_LAPSE_RATE = 0.0098
    WET_LAPSE_RATE = 0.005
    
    """ GUARD 2: Saturated (Wet) air cools slower because condensation releases heat """
    if is_saturated:
        return t_surface_k - (WET_LAPSE_RATE * altitude_m)
    
    """ HAPPY PATH: Dry adiabatic cooling """
    return t_surface_k - (DRY_LAPSE_RATE * altitude_m)

@njit(fastmath=True)
def calculate_radiative_cooling_grid(
    lwp_array_g_m2, t_start_c_array, cloud_fraction_array, hours=12.0
):
    """
    Batched calculation of net temperature drop due to radiative cooling.
    Processes entire grid arrays simultaneously.
    """
    lwp = xp.array(lwp_array_g_m2, dtype=xp.float64)
    t_start = xp.array(t_start_c_array, dtype=xp.float64)
    c_frac = xp.array(cloud_fraction_array, dtype=xp.float64)
    SIGMA = 5.670374419000000e-8
    SPECIFIC_HEAT_AIR = 1005.0 # J/(kg*K)
    emissivity = 1.0 - xp.exp(-0.022 * lwp)
    net_flux = emissivity * SIGMA * ((t_start + 273.15) ** 4) * c_frac
    total_seconds = hours * 3600.0
    temp_drop = (net_flux * total_seconds) / (SPECIFIC_HEAT_AIR * 1000.0)
    final_temp = t_start - temp_drop
    if HAS_GPU:
        return {
            "drop_c": xp.round(temp_drop, 15).get().tolist(),
            "final_t": xp.round(final_temp, 15).get().tolist(),
            "net_flux": xp.round(net_flux, 15).get().tolist()
        }
    else:
        return {
            "drop_c": xp.round(temp_drop, 15).tolist(),
            "final_t": xp.round(final_temp, 15).tolist(),
            "net_flux": xp.round(net_flux, 15).tolist()
        }

@njit(fastmath=True)
def run_cloud_temp_layer(telemetry_override=None):
    """Main orchestration function reporting to Boeing payload."""
    print("☁️ Running Batched Cloud Radiative Cooling Layer...")
    lwps = [50.0]
    temps = [15.0]
    fractions = [0.8]
    if telemetry_override:
        if isinstance(telemetry_override, dict):
            lwps = [telemetry_override.get('lwp', 50.0)]
            temps = [telemetry_override.get('temp_c', 15.0)]
            fractions = [telemetry_override.get('cloud_fraction', 0.8)]
        elif isinstance(telemetry_override, list):
            lwps = [t.get('lwp', 50.0) for t in telemetry_override]
            temps = [t.get('temp_c', 15.0) for t in telemetry_override]
            fractions = [t.get('cloud_fraction', 0.8) for t in telemetry_override]
    results = calculate_radiative_cooling_grid(lwps, temps, fractions)
    payload = {
        "initial_temp_c": temps[0],
        "liquid_water_path_g_m2": lwps[0],
        "final_predicted_temp_c": results['final_t'][0],
        "total_temperature_drop_c": results['drop_c'][0],
        "downwelling_longwave_flux_w_m2": results['net_flux'][0]
    }
    telemetry_link.update_global_state("atmospheric_models", "cloud_cooling", payload)
    print(f"Cloud layer cooling grid reported to global state.")
    return payload
if __name__ == "__main__":
    print("=================================================================")
    print("          CLOUD RADIATIVE COOLING ENGINE (BATCHED)               ")
    print("=================================================================")
    test_lwp = [100.0, 50.0, 5.0]
    test_temps = [15.0, 10.0, -20.0]
    test_frac = [0.9, 0.4, 0.1]
    results = calculate_radiative_cooling_grid(test_lwp, test_temps, test_frac)
    for i in range(3):
        print(f"Sector {i+1}: Start: {test_temps[i]}°C -> End: {round(results['final_t'][i], 2)}°C")
