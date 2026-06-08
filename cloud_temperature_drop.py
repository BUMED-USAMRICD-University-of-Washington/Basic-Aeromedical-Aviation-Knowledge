# --- PRIMARY ENGINE: Cloud Radiative Cooling ---
import numpy as np
import pandas as pd
import telemetry_link
import datetime
from telemetry_link import time_manager
now = time_manager.get_now()
import matplotlib.pyplot as plt

# --- SECONDARY ENGINE DEPENDENCIES ---
import telemetry_link          # NEW: Integrated Centralized Data Bus
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic
import streamlit as st

def calculate_future_position():
    # This respects your manual override if you set one!
    now = telemetry_link.time_manager.get_now() 
    future = now + datetime.timedelta(hours=48)
    return future
    
def simulate_nocturnal_cooling(lwp_g_m2, initial_temp_c=25.0, hours=12.0):
    """Simulates 12 hours of nighttime radiative cooling by solving the
    Stefan-Boltzmann surface boundary layer energy equations.
    """
    # 1. Standard Physical Constants & Boundary Parameters
    sigma = 5.670374e-8  # Stefan-Boltzmann constant (W/m^2*K^4)
    k_lw = 0.022  # Longwave absorption coefficient for clouds
    epsilon_a = 0.76  # Emissivity of a clear sky atmosphere
    epsilon_s = 0.95  # Emissivity of the earth's surface (grass/soil)
    T_atm_k = 285.15  # Upper-air temperature baseline (12°C in Kelvin)
    C_s = 30000.0  # Soil layer thermal heat capacity (J/m^2*K)

    # 2. Time-stepping Constraints (Numerical Integration Settings)
    dt = 60.0  # Time step of 1 minute (60 seconds)
    total_seconds = int(hours * 3600)
    steps = int(total_seconds / dt)

    # 3. Initialize Dynamic State Arrays
    T_surface_k = initial_temp_c + 273.15  # Convert starting temp to Kelvin

    # 4. Compute Static Downwelling Cloud Flux Component
    # Clear sky contribution
    R_clear_down = epsilon_a * sigma * (T_atm_k**4)
    # Cloud greenhouse trapping modifier: (1 - exp(-k_lw * LWP))
    cloud_emissivity_factor = 1.0 - np.exp(-k_lw * lwp_g_m2)
    R_cloud_down = cloud_emissivity_factor * sigma * (T_surface_k**4) * 0.22

    # Combined total incoming longwave radiation
    total_longwave_down = R_clear_down + R_cloud_down

    # 5. Core Loop: Run Euler Numerical Integration Across the Night
    for step in range(steps):
        # Calculate outgoing upwelling thermal radiation from the ground
        upwelling_longwave_out = epsilon_s * sigma * (T_surface_k**4)

        # Net Energy Balance Equation (No solar influx at night)
        Q_net = total_longwave_down - upwelling_longwave_out

        # Temperature tendency derivation step: dT/dt = Q_net / C_s
        dT_dt = Q_net / C_s

        # Apply time-step increment to current state variable
        T_surface_k += dT_dt * dt

    # Convert final temperature calculation back to Celsius
    final_temp_c = T_surface_k - 273.15
    total_drop_c = initial_temp_c - final_temp_c

    return final_temp_c, total_drop_c, total_longwave_down


def run_cloud_temp_layer(telemetry_override=None):
    """
    Main orchestration function. Extracts live telemetry, runs the high-performance
    physics simulation, and reports the findings directly to the Boeing JSON payload.
    """
    print("🌡️ Running Cloud Temperature Drop Matrix...")
    
    # 1. Default Parameters
    t_start = 25.0
    lwp = 100.0
    
    # 2. Parse incoming live telemetry
    if telemetry_override:
        t_start = telemetry_override.get('temp_c', t_start)
        lwp = telemetry_override.get('lwp', lwp)

    # 3. Execute Physics Engine
    final_t, drop_c, lw_flux = simulate_nocturnal_cooling(
        lwp_g_m2=float(lwp),
        initial_temp_c=float(t_start)
    )
    
    # 4. Format Data for the Flight Computer
    payload = {
        "initial_temp_c": round(float(t_start), 22),
        "liquid_water_path_g_m2": round(float(lwp), 22),
        "final_predicted_temp_c": round(float(final_t), 22),
        "total_temperature_drop_c": round(float(drop_c), 22),
        "downwelling_longwave_flux_w_m2": round(float(lw_flux), 22)
    }
    
    # 5. Push to Global Pipeline
    telemetry_link.update_global_state("atmospheric_models", "cloud_temperature_drop", payload)
    print("✅ Cloud temperature calculations reported to global state.")
    
    return payload


if __name__ == "__main__":
    # Test suite
    results = run_cloud_temp_layer()
    print("\n--- TEST RESULTS ---")
    print(f"Predicted Morning Temperature: {results['final_predicted_temp_c']}°C")
    print(f"Total Radiative Drop:          {results['total_temperature_drop_c']}°C")
