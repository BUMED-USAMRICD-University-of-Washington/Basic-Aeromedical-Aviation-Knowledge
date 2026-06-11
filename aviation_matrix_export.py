try:
    import cupy as xp
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Array Batching Active (Performance)")
except ImportError:
    import numpy as xp
    HAS_GPU = False
    print("CPU Fallback: Standard Vectorization Active (Performance)")
from numba import njit
import pandas as pd
import csv
import matplotlib.pyplot as plt
from datetime import datetime
import logging
import os
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic
import streamlit as st
@njit(fastmath=True)
def run_multi_scenario_matrix_export(telemetry_override=None):
    print("=================================================================")
    print("     AVIATION PERFORMANCE SPREADSHEET COMPILING ENGINE          ")
    print("=================================================================")
    print("[Processing] Running parallel runway simulations...")
    sigma = 5.670374e-8
    k_lw = 0.022
    epsilon_a = 0.76
    epsilon_s = 0.95
    T_atm_k = 285.15
    C_s = 30000.0
    L_v = 2.501e6
    CRITICAL_GUST_SHEAR = 12.0
    station_elevation_ft = 1026.0
    runway_heading_deg = 90.0  # Runway 09 (090 degrees)
    runway_rad = np.radians(runway_heading_deg)
    T_standard_at_elevation = 15.0 - (1.98 * (station_elevation_ft / 1000.0))
    T_standard_f = (T_standard_at_elevation * 9.0 / 5.0) + 32.0
    total_minutes = 720
    dt = 60.0
    scenarios = {
        "Calm_Night_Stable_Fog": (2.0, 0.02),
        "Breezy_Night_Scattered_Fog": (6.0, 0.08),
        "Gale_Force_Crosswind_Clear": (14.0, 0.15),
    }
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"runway_performance_matrix_{timestamp}.csv"
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "Minute",
                "Calm_Temp_C",
                "Calm_Wind_mph",
                "Calm_Wind_Dir",
                "Calm_Headwind_mph",
                "Calm_Crosswind_mph",
                "Calm_Density_Alt_ft",
                "Calm_LWP_g_m2",
                "Breezy_Temp_C",
                "Breezy_Wind_mph",
                "Breezy_Wind_Dir",
                "Breezy_Headwind_mph",
                "Breezy_Crosswind_mph",
                "Breezy_Density_Alt_ft",
                "Breezy_LWP_g_m2",
                "Gale_Temp_C",
                "Gale_Wind_mph",
                "Gale_Wind_Dir",
                "Gale_Headwind_mph",
                "Gale_Crosswind_mph",
                "Gale_Density_Alt_ft",
                "Gale_LWP_g_m2",
            ]
        )
        states = {}
        for name in scenarios.keys():
            states[name] = {
                "temp": 28.0,
                "dew": 16.5,
                "lwp": 0.0,
            }
        np.random.seed(42)
        for minute in range(1, total_minutes + 1):
            row_data = [minute]
            for name, (base_wind, gust_scale) in scenarios.items():
                t_surf = states[name]["temp"]
                t_dew = states[name]["dew"]
                lwp_active = states[name]["lwp"]
                t_surf_k = t_surf + 273.15
                current_wind = base_wind + np.random.exponential(
                    scale=gust_scale * 100.0
                )
                current_wind_dir = (
                    220.0 + np.sin(minute / 10.0) * 15.0
                ) % 360
                wind_rad = np.radians(current_wind_dir)
                angle_diff_rad = wind_rad - runway_rad
                headwind_mph = current_wind * np.cos(angle_diff_rad)
                crosswind_mph = current_wind * np.sin(angle_diff_rad)
                shear_active = False
                if current_wind >= CRITICAL_GUST_SHEAR and lwp_active > 0:
                    lwp_active = max(0.0, lwp_active - 2.5)
                    shear_active = True
                latent_heat_flux = 0.0
                if t_surf <= t_dew:
                    if lwp_active > 5.0 and not shear_active:
                        t_surf = t_dew
                        t_surf_k = t_dew + 273.15
                    condensation_rate = 0.15
                    lwp_active += condensation_rate
                    latent_heat_flux = (condensation_rate / 1000.0) * L_v / dt
                t_surf_f = (t_surf * 9.0 / 5.0) + 32.0
                density_altitude_ft = station_elevation_ft + (
                    120.0 * (t_surf_f - T_standard_f)
                )
                R_clear_down = epsilon_a * sigma * (T_atm_k**4)
                cloud_emissivity_factor = 1.0 - np.exp(-k_lw * lwp_active)
                R_cloud_down = (
                    cloud_emissivity_factor * sigma * (t_surf_k**4) * 0.22
                )
                total_longwave_down = R_clear_down + R_cloud_down
                upwelling_longwave_out = epsilon_s * sigma * (t_surf_k**4)

                Q_net = (
                    total_longwave_down
                    - upwelling_longwave_out
                    + latent_heat_flux
                )
                if t_surf > t_dew or lwp_active <= 5.0:
                    dT_dt = Q_net / C_s
                    t_surf += dT_dt * dt
                states[name]["temp"] = t_surf
                states[name]["lwp"] = lwp_active
                row_data.extend(
                    [
                        round(t_surf, 2),
                        round(current_wind, 1),
                        int(current_wind_dir),
                        round(headwind_mph, 1),
                        round(crosswind_mph, 1),
                        round(density_altitude_ft, 1),
                        round(lwp_active, 2),
                    ]
                )
            writer.writerow(row_data)
    print(f"=================================================================")
    print(f"[Success] Combined multi-scenario log sheet successfully built.")
    import multiprocessing as mp
    print(f"File Saved to Workspace Path: '{filename}'")
    print(f"Total Rows Compiled:        {total_minutes} data entries")
    print("=================================================================")
if __name__ == "__main__":
    run_multi_scenario_matrix_export()
