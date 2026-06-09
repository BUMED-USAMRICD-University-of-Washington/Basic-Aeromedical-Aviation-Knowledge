import telemetry_link
import multiprocessing as mp
from dynamic_memory_cache import DynamicMemoryCache
shared_cache = DynamicMemoryCache(percentage=0.14)
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import aviation_physics
import aviation_telemetry
import aircraft_perf
import sensor_thermodynamics
import aerodynamic_matrix
from numba import njit
@njit(fastmath=True)
try:
    import cupy as xp
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Array Batching Active (Performance)")
except ImportError:
    import numpy as xp
    HAS_GPU = False
    print("CPU Fallback: Standard Vectorization Active (Performance)")
def calculate_performance_envelope_grid(
    airspeed_array_knots, altitude_array_ft, drag_coefficient_array
):
    """
    Batched calculation of the flight performance envelope.
    Computes required power (P_req) and fuel flow for an entire 
    matrix of speed/altitude combinations simultaneously.
    """
    v_kts = xp.array(airspeed_array_knots, dtype=xp.float64)
    alt_ft = xp.array(altitude_array_ft, dtype=xp.float64)
    c_d = xp.array(drag_coefficient_array, dtype=xp.float64)
    rho_0 = 1.225 # kg/m^3 (SL)
    rho_array = rho_0 * xp.exp(-alt_ft / 28000.0) 
    v_mps = v_kts * 0.514444
    S = 100.0
    p_req_watts = 0.5 * rho_array * (v_mps ** 3) * S * c_d
    fuel_flow_kg_h = p_req_watts * 0.0003 
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
    print("Running Batched Aircraft Performance Layer...")
    speeds = [200.0]
    alts = [10000.0]
    drag = [0.025]
    if telemetry_override:
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
    test_speeds = [120.0, 350.0, 450.0]
    test_alts = [500.0, 35000.0, 15000.0]
    test_cd = [0.05, 0.02, 0.03]
    res = calculate_performance_envelope_grid(test_speeds, test_alts, test_cd)
    for i in range(3):
        print(f"Profile {i+1}: {test_speeds[i]}kts at {test_alts[i]}ft -> Power Required: {round(res['p_req_w'][i], 0)} W")
