# --- PRIMARY ENGINE: [Model Name] ---
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- SECONDARY ENGINE DEPENDENCIES ---
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic
import streamlit as st

from numba import njit

@njit(fastmath=True) # fastmath enables hardware-level floating point optimizations
def calculate_density_and_cooling(temp_c, wind_mph, relative_humidity=0.50):
    # Your existing pure-math logic here
    T_kelvin = temp_c + 273.15
    # ... rest of your calculations
    return air_density, wind_chill_c, cooling_delta

try:
    import cupy as np  # Attempt to use GPU-accelerated array math
    print("🚀 NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np # Fallback to standard CPU math
    print("⚡ Using CPU (NVIDIA acceleration not detected)")

def calculate_density_and_cooling(telemetry_override=None, temp_c, wind_mph, relative_humidity=0.50):
    """
    Solves the combined gas density and convective wind cooling equations
    for atmospheric weather analysis.
    """
    # --- 1. AIR DENSITY MATRIX CALCULATIONS ---
    T_kelvin = temp_c + 273.15
    P_total = 101325.0  # Standard sea level pressure in Pascals
    
    # Magnus-Tetens formula to calculate water vapor partial pressures
    es = 611.2 * np.exp((17.67 * temp_c) / (temp_c + 243.5))
    Pv = es * relative_humidity
    Pd = P_total - Pv
    
    R_d = 287.05
    R_v = 461.495
    
    # Execute the Density Matrix Core
    air_density = (Pd / (R_d * T_kelvin)) + (Pv / (R_v * T_kelvin))
    
    # --- 2. WIND CHILL CONVECTIVE HEAT EXTRAPOLATION ---
    # Convert metric inputs to imperial for standard NWS equation limits
    T_fahrenheit = (temp_c * 9.0/5.0) + 32.0
    
    if T_fahrenheit <= 50.0 and wind_mph >= 3.0:
        # Engage NWS cooling curve equation layer
        v_factor = wind_mph ** 0.16
        wind_chill_f = 35.74 + (0.6215 * T_fahrenheit) - (35.75 * v_factor) + (0.4275 * T_fahrenheit * v_factor)
        wind_chill_c = (wind_chill_f - 32.0) * 5.0/9.0
        cooling_delta = temp_c - wind_chill_c
    else:
        wind_chill_c = temp_c
        cooling_delta = 0.0
        
    return air_density, wind_chill_c, cooling_delta

if __name__ == "__main__":
    print("================================================================")
    print("         NWS WIND DENSITY & COOLING INDEX SOLVER                ")
    print("================================================================")
    
    # Test conditions: Cold morning setup (4.0°C / ~39°F)
    test_temp_c = 4.0
    wind_scenarios = [5.0, 15.0, 35.0]  # Light Breeze, Steady Wind, Gale Force Shear
    
    print(f"Baseline Temperature: {test_temp_c}°C | Relative Humidity: 50%\n")
    
    for wind in wind_scenarios:
        density, chill, delta = calculate_density_and_cooling(test_temp_c, wind)
        print(f"💨 Wind Speed Velocity: {wind:<4} mph")
        print(f"   -> Calculated Air Density:   {density:.4f} kg/m³")
        print(f"   -> Resulting Wind Chill:     {chill:.2f}°C")
        print(f"   -> Convective Degree Drop:   -{delta:.2f}°C variation")
        print("-" * 55)
