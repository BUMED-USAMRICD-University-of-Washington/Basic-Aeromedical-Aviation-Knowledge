import telemetry_link
# memory_manager.py
from dynamic_memory_cache import DynamicMemoryCache

# Create one shared cache instance for the whole app
shared_cache = DynamicMemoryCache(percentage=0.25)

import multiprocessing as mp
# --- PRIMARY ENGINE: [Model Name] ---
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- SECONDARY ENGINE DEPENDENCIES ---
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic

from numba import njit

@njit(fastmath=True) # fastmath enables hardware-level floating point optimizations

try:
    import cupy as np  # Attempt to use GPU-accelerated array math
    print("🚀 NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np # Fallback to standard CPU math
    print("⚡ Using CPU (NVIDIA acceleration not detected)")
    
# --- HARDWARE ABSTRACTION LAYER (HAL) ---
try:
    import cupy as xp  # NVIDIA GPU Acceleration
    HAS_GPU = True
    print("🚀 NVIDIA CUDA Cores Engaged: Array Batching Active (Performance)")
except ImportError:
    import numpy as xp # CPU Fallback
    HAS_GPU = False
    print("⚡ CPU Fallback: Standard Vectorization Active (Performance)")

def calculate_performance_envelope_grid(
    airspeed_array_knots, altitude_array_ft, drag_coefficient_array
):
    """
    Batched calculation of the flight performance envelope.
    Computes required power (P_req) and fuel flow for an entire 
    matrix of speed/altitude combinations simultaneously.
    """
    # 1. Load data to hardware (15-Decimal Precision Standard)
    v_kts = xp.array(airspeed_array_knots, dtype=xp.float64)
    alt_ft = xp.array(altitude_array_ft, dtype=xp.float64)
    c_d = xp.array(drag_coefficient_array, dtype=xp.float64)
    
    # 2. Physics Constants
    # Air density reduction with altitude (Approximation)
    rho_0 = 1.225 # kg/m^3 (SL)
    # Scale density by altitude
    rho_array = rho_0 * xp.exp(-alt_ft / 28000.0) 
    
    # 3. Batched Kinematic Equations
    v_mps = v_kts * 0.514444
    # Power required: P_req = 0.5 * rho * V^3 * S * C_d
    # Assuming Wing Area (S) = 100 m^2
    S = 100.0
    p_req_watts = 0.5 * rho_array * (v_mps ** 3) * S * c_d
    
    # Fuel flow estimation (linear approximation)
    fuel_flow_kg_h = p_req_watts * 0.0003 

    # 4. Return to CPU host
    if HAS_GPU:
        return {
            "p_req_w": xp.round(p_req_watts, 15).get().tolist(),
            "fuel_flow": xp.round(fuel_flow_kg_h, 15).get().tolist()
        }
    else:
        return {
            "p_req_w": xp.round(p_req_watts, 15).tolist(),
            "fuel_flow": xp.round(fuel_flow_kg_h, 15).tolist()
        }

def run_perf_layer(telemetry_override=None):
    """Orchestrator for Boeing/NASA payload compliance."""
    print("✈️ Running Batched Aircraft Performance Layer...")
    
    # Defaults
    speeds = [200.0]
    alts = [10000.0]
    drag = [0.025]
    
    if telemetry_override:
        # Supports batch overrides
        speeds = [t.get('airspeed', 200.0) for t in telemetry_override] if isinstance(telemetry_override, list) else [telemetry_override.get('airspeed', 200.0)]
        alts = [t.get('altitude', 10000.0) for t in telemetry_override] if isinstance(telemetry_override, list) else [telemetry_override.get('altitude', 10000.0)]
        drag = [t.get('cd', 0.025) for t in telemetry_override] if isinstance(telemetry_override, list) else [telemetry_override.get('cd', 0.025)]

    results = calculate_performance_envelope_grid(speeds, alts, drag)
    
    payload = {
        "p_req_watts": results['p_req_w'][0],
        "fuel_flow_kg_h": results['fuel_flow'][0],
        "airspeed_kts": speeds[0],
        "altitude_ft": alts[0]
    }
    
    telemetry_link.update_global_state("performance_models", "flight_envelope", payload)
    return payload

if __name__ == "__main__":
    print("================================================================")
    print("      AIRCRAFT PERFORMANCE ENVELOPE GENERATOR (BATCHED)         ")
    print("================================================================")
    
    # Test batching across a flight profile: [Takeoff, Cruise, High-Speed Descent]
    test_speeds = [120.0, 350.0, 450.0]
    test_alts = [500.0, 35000.0, 15000.0]
    test_cd = [0.05, 0.02, 0.03]
    
    res = calculate_performance_envelope_grid(test_speeds, test_alts, test_cd)
    
    for i in range(3):
        print(f"Profile {i+1}: {test_speeds[i]}kts at {test_alts[i]}ft -> Power Required: {round(res['p_req_w'][i], 0)} W")
