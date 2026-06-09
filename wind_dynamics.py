try:
    import cupy as xp
    HAS_GPU = True
except ImportError:
    import numpy as xp
    HAS_GPU = False
import pandas as pd
import matplotlib.pyplot as plt
from numba import njit
@njit(fastmath=True)
import telemetry_link
import aviation_physics
import aircraft_perf
import aviation_telemetry
import aerodynamic_matrix
import streamlit as st
import sensor_thermodynamics
def calculate_density_and_cooling(temp_c, wind_mph, relative_humidity=0.50):
    """
    Solves the combined gas density and convective wind cooling equations
    for atmospheric weather analysis.
    """
    T_kelvin = temp_c + 273.15
    P_total = 101325.0
    es = 611.2 * np.exp((17.67 * temp_c) / (temp_c + 243.5))
    Pv = es * relative_humidity
    Pd = P_total - Pv
    R_d = 287.05
    R_v = 461.495
    air_density = (Pd / (R_d * T_kelvin)) + (Pv / (R_v * T_kelvin))
    T_fahrenheit = (temp_c * 9.0/5.0) + 32.0
    if T_fahrenheit <= 50.0 and wind_mph >= 3.0:
        v_factor = wind_mph ** 0.16
        wind_chill_f = 35.74 + (0.6215 * T_fahrenheit) - (35.75 * v_factor) + (0.4275 * T_fahrenheit * v_factor)
        wind_chill_c = (wind_chill_f - 32.0) * 5.0/9.0
        cooling_delta = temp_c - wind_chill_c
    else:
        wind_chill_c = temp_c
        cooling_delta = 0.0
    return air_density, wind_chill_c, cooling_delta
def run_wind_layer(telemetry_override=None):
    """
    Main orchestration function. Extracts live telemetry, runs the high-performance
    physics simulation, and reports the findings directly to the Boeing JSON payload.
    """
    print("Running Wind Dynamics Matrix...")
    temp = 4.0
    wind = 15.0
    rh = 0.50
    if telemetry_override:
        temp = telemetry_override.get('temp_c', temp)
        wind = telemetry_override.get('wind_mph', wind)
        raw_rh = telemetry_override.get('rh_pct', rh * 100.0)
        rh = raw_rh / 100.0 if raw_rh > 1.0 else raw_rh
    density, chill, delta = calculate_density_and_cooling(
        temp_c=temp, 
        wind_mph=wind, 
        relative_humidity=rh
    )
    payload = {
        "base_temp_c": temp,
        "wind_speed_mph": wind,
        "relative_humidity": rh,
        "air_density_kg_m3": round(float(density), 4),
        "wind_chill_c": round(float(chill), 2),
        "convective_cooling_delta_c": round(float(delta), 2)
    }
    telemetry_link.update_global_state("dynamics", "wind_matrix", payload)
    print("Wind dynamics calculations reported to global state.")
    return payload
if __name__ == "__main__":
    print("================================================================")
    print("         NWS WIND DENSITY & COOLING INDEX SOLVER                ")
    print("================================================================")
    test_temp_c = 4.0
    wind_scenarios = [5.0, 15.0, 35.0]
    print(f"Baseline Temperature: {test_temp_c}°C | Relative Humidity: 50%\n")
    for wind in wind_scenarios:
        density, chill, delta = calculate_density_and_cooling(test_temp_c, wind)
        print(f"💨 Wind Speed Velocity: {wind:<4} mph")
        print(f"   -> Calculated Air Density:   {density:.4f} kg/m³")
        print(f"   -> Resulting Wind Chill:     {chill:.2f}°C")
        print(f"   -> Convective Degree Drop:   -{delta:.2f}°C variation")
        print("-" * 55)
