# --- PRIMARY ENGINE: Fog Thermodynamics ---
import pandas as pd
import matplotlib.pyplot as plt
from numba import njit
import telemetry_link
import datetime
from telemetry_link import time_manager
now = time_manager.get_now()
# --- SECONDARY ENGINE DEPENDENCIES ---
import telemetry_link          # NEW: Integrated Centralized Data Bus
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic
import streamlit as st
from datetime import datetime, timedelta
try:
    import cupy as xp  # NVIDIA GPU Acceleration
    HAS_GPU = True
    print("🚀 NVIDIA CUDA Cores Engaged: Array Batching Active (Fog)")
except ImportError:
    import numpy as xp # CPU Fallback
    HAS_GPU = False
    print("⚡ CPU Fallback: Standard Vectorization Active (Fog)")

def simulate_cooling_grid(
    temp_array_c, dewpoint_array_c, lwp_array, hours=12.0
):
    """
    Batched 12-hour numerical integration loop.
    Simulates nighttime cooling and dynamic fog formation across an entire grid simultaneously.
    """
    # 1. Load data to active hardware (15-decimal precision standard)
    T_surf = xp.array(temp_array_c, dtype=xp.float64)
    T_dew = xp.array(dewpoint_array_c, dtype=xp.float64)
    lwp_active = xp.array(lwp_array, dtype=xp.float64)
    
    # Grid size tracking for formation hours
    grid_size = len(T_surf)
    fog_formed_at_step = xp.full(grid_size, -1.0, dtype=xp.float64) 
    
    # 2. Physical & Thermodynamic Constants
    sigma = 5.670374e-8  
    k_lw = 0.022  
    epsilon_a = 0.76  
    epsilon_s = 0.95  
    T_atm_k = 285.15  
    C_s = 30000.0  
    L_v = 2.501e6  
    
    # 3. Time-stepping Constraints
    dt = 60.0 # 1-minute steps
    steps = int((hours * 3600) / dt)
    condensation_rate = 0.15

    # 4. Batched Numerical Integration Loop
    for step in range(steps):
        T_surf_k = T_surf + 273.15
        
        # Boolean mask: Which grid points have hit the dew point?
        # This allows the GPU to branch logic without Python 'if' statements
        is_saturated = T_surf <= T_dew
        
        # Log the exact hour of formation for newly saturated points
        current_hour = step * (dt / 3600.0)
        newly_saturated = is_saturated & (fog_formed_at_step == -1.0)
        fog_formed_at_step = xp.where(newly_saturated, current_hour, fog_formed_at_step)
        
        # 🛑 CAP 1: Force locked temperatures to the dew point
        T_surf = xp.where(is_saturated, T_dew, T_surf)
        T_surf_k = xp.where(is_saturated, T_dew + 273.15, T_surf_k)
        
        # 💨 CAP 2: Condense liquid water path where saturated
        lwp_active = xp.where(is_saturated, lwp_active + condensation_rate, lwp_active)
        
        # 🔥 CAP 3: Release latent heat 
        latent_heat_flux = xp.where(is_saturated, (condensation_rate / 1000.0) * L_v / dt, 0.0)
        
        # 5. Compute Fluxes (Array Math)
        R_clear_down = epsilon_a * sigma * (T_atm_k**4)
        cloud_emissivity_factor = 1.0 - xp.exp(-k_lw * lwp_active)
        R_cloud_down = cloud_emissivity_factor * sigma * (T_surf_k**4) * 0.22
        
        total_longwave_down = R_clear_down + R_cloud_down
        upwelling_longwave_out = epsilon_s * sigma * (T_surf_k**4)
        
        # 6. Net Energy Balance
        Q_net = total_longwave_down - upwelling_longwave_out + latent_heat_flux
        
        # 7. Apply cooling ONLY to unsaturated points
        dT_dt = Q_net / C_s
        T_surf = xp.where(~is_saturated, T_surf + (dT_dt * dt), T_surf)

    # 8. Return to CPU host
    total_drop_c = xp.array(temp_array_c) - T_surf
    
    # Format None for unformed fog to match original output
    fog_hours_cpu = fog_formed_at_step.get().tolist() if HAS_GPU else fog_formed_at_step.tolist()
    fog_hours_clean = [h if h != -1.0 else None for h in fog_hours_cpu]

    if HAS_GPU:
        return {
            "final_temp_c": xp.round(T_surf, 15).get().tolist(),
            "drop_c": xp.round(total_drop_c, 15).get().tolist(),
            "final_lwp": xp.round(lwp_active, 15).get().tolist(),
            "fog_hour": fog_hours_clean
        }
    else:
        return {
            "final_temp_c": xp.round(T_surf, 15).tolist(),
            "drop_c": xp.round(total_drop_c, 15).tolist(),
            "final_lwp": xp.round(lwp_active, 15).tolist(),
            "fog_hour": fog_hours_clean
        }

def run_fog_layer(telemetry_override=None):
    """Main orchestration function reporting to Boeing payload."""
    print("☁️ Running Batched Fog Thermodynamics Layer...")
    
    # Base fallback lists
    temps = [25.0]
    dews = [12.0]
    lwps = [0.0]
    
    if telemetry_override:
        # Check if override is a single dict or a batch list
        if isinstance(telemetry_override, dict):
            temps = [telemetry_override.get('temp_c', 25.0)]
            dews = [telemetry_override.get('dewpoint_c', 12.0)]
            lwps = [telemetry_override.get('lwp', 0.0)]
        elif isinstance(telemetry_override, list):
            temps = [t.get('temp_c', 25.0) for t in telemetry_override]
            dews = [t.get('dewpoint_c', 12.0) for t in telemetry_override]
            lwps = [t.get('lwp', 0.0) for t in telemetry_override]

    results = simulate_cooling_grid(temps, dews, lwps)
    
    # Extract the first element to maintain backward compatibility with JSON scalar payloads
    payload = {
        "initial_temp_c": temps[0],
        "initial_dew_c": dews[0],
        "final_temp_c": results['final_temp_c'][0],
        "temperature_drop_c": results['drop_c'][0],
        "final_liquid_water_path_g_m2": results['final_lwp'][0],
        "fog_formation_hour": results['fog_hour'][0],
        "fog_risk_active": bool(results['fog_hour'][0] is not None)
    }
    
    telemetry_link.update_global_state("atmospheric_models", "fog_thermodynamics", payload)
    print(f"✅ Fog layer grid calculations reported to global state.")
    return payload

if __name__ == "__main__":
    print("=================================================================")
    print("      NWS BOUNDARY LAYER SATURATION & FOG ENGINE (BATCHED)       ")
    print("=================================================================")
    
    # Testing 3 different geographic sectors simultaneously
    test_temps = [25.0, 15.0, 10.0]
    test_dews = [12.0, 14.0, 9.5]
    test_lwps = [0.0, 0.0, 0.0]
    
    print(f"Simulating 12-Hour Night for 3 sectors...")
    print(f"Initial Temps: {test_temps}")
    print(f"Initial Dews:  {test_dews}\n")
    
    batch_results = simulate_cooling_grid(test_temps, test_dews, test_lwps)
    
    for i in range(3):
        status = f"Formed at Hour {round(batch_results['fog_hour'][i], 2)}" if batch_results['fog_hour'][i] else "No Fog"
        print(f"Sector {i+1}: Final Temp: {round(batch_results['final_temp_c'][i], 2)}°C | Status: {status}")
