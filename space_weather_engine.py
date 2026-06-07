# --- PRIMARY ENGINE: Space Weather ---
import pandas as pd
import matplotlib.pyplot as plt
from numba import njit
import multiprocessing as mp

# --- SECONDARY ENGINE DEPENDENCIES ---
import telemetry_link          # NEW: Integrated Centralized Data Bus
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic
import streamlit as st

try:
    import cupy as np  # Attempt to use GPU-accelerated array math
    print("🚀 NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np # Fallback to standard CPU math
    print("⚡ Using CPU (NVIDIA acceleration not detected)")


# space_weather_engine.py
# Tracks astronomical and solar forcing indices to offset city base grids

@njit(fastmath=True) # fastmath enables hardware-level floating point optimizations
def calculate_astronomical_offsets(solar_flux_f107, galactic_ray_count):
    """
    Calculates the fractional shift in Total Solar Irradiance (TSI)
    and cosmic ionization scaling factor from space gas tracking.
    """
    # Calculates the fractional shift in Total Solar Irradiance (TSI)
    # over the 11-year solar cycle
    delta_tsi_forcing = (solar_flux_f107 / 1361.0) * 0.25
    
    # Calculates cosmic ionization scaling factor from space gas tracking
    cosmic_variance = galactic_ray_count * 1.38e-23
    
    return delta_tsi_forcing, cosmic_variance


def run_space_layer(telemetry_override=None):
    """
    Main orchestration function. Extracts live telemetry, runs the high-performance
    physics simulation, and reports the findings directly to the Boeing JSON payload.
    """
    print("🌌 Running Space Weather Engine...")
    
    # 1. Default Space Weather Baseline (Average Solar Day)
    f107_flux = 150.0  # Solar Flux Units (sfu)
    gcr_count = 5000.0 # Galactic Cosmic Ray counts per minute
    
    # 2. Parse incoming live telemetry
    if telemetry_override:
        f107_flux = telemetry_override.get('solar_flux_f107', f107_flux)
        gcr_count = telemetry_override.get('galactic_ray_count', gcr_count)

    # 3. Execute GPU/FastMath Physics Engine
    tsi_forcing, cosmic_var = calculate_astronomical_offsets(
        solar_flux_f107=float(f107_flux), 
        galactic_ray_count=float(gcr_count)
    )
    
    total_offset = tsi_forcing + cosmic_var
    
    # 4. Format Data for the Flight Computer
    payload = {
        "solar_flux_f107_sfu": round(float(f107_flux), 2),
        "galactic_ray_count_cpm": round(float(gcr_count), 2),
        "delta_tsi_forcing_w_m2": round(float(tsi_forcing), 6),
        "cosmic_ionization_variance": float(cosmic_var),
        "total_astronomical_offset": float(total_offset)
    }
    
    # 5. Push to Global Pipeline
    telemetry_link.update_global_state("atmospheric_models", "space_weather", payload)
    print("✅ Space Weather calculations reported to global state.")
    
    return payload


if __name__ == "__main__":
    print("================================================================")
    print("         SOLAR & COSMIC ASTRONOMICAL OFFSET TRACKER             ")
    print("================================================================")
    
    # Run a local test iteration
    results = run_space_layer()
    
    print("\n--- TEST RESULTS ---")
    print(f"Solar Flux (F10.7):   {results['solar_flux_f107_sfu']} sfu")
    print(f"Galactic Ray Count:   {results['galactic_ray_count_cpm']} cpm")
    print(f"TSI Forcing Delta:    {results['delta_tsi_forcing_w_m2']} W/m^2")
    print(f"Cosmic Variance:      {results['cosmic_ionization_variance']}")
    print(f"Total Model Offset:   {results['total_astronomical_offset']}")
