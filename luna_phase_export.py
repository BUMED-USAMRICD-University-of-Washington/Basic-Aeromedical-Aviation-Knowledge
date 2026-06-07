# --- PRIMARY ENGINE: [Model Name] ---
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import csv

# --- SECONDARY ENGINE DEPENDENCIES ---
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

def run_and_save_lunar_phase(telemetry_override=None):
    print("--- Lunar Phase Signal Spreadsheet Engine ---")
    start_index_day = float(
        input("Enter start index day of lunar calendar (0 = New Moon): ")
    )

from numba import njit

@njit(fastmath=True) # fastmath enables hardware-level floating point optimizations

    # Calculate across a full 29.53-day cycle using 100 evaluation steps
    t = np.linspace(start_index_day, start_index_day + 29.53, 100)
    P_syn = 29.53

    A_grav, phi_grav = 0.08, 3.5
    A_therm, phi_therm = 0.03, 1.0

    gravity_wave = A_grav * np.cos((4 * np.pi / P_syn) * t - phi_grav)
    thermal_wave = A_therm * np.cos((2 * np.pi / P_syn) * t - phi_therm)
    total_signal = gravity_wave + thermal_wave

    filename = "lunar_synodic_phase_matrix.csv"

    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "Days_Since_New_Moon",
                "Gravitational_Component_Variance",
                "Thermal_Albedo_Variance",
                "Total_Lunar_Signal_Anomaly",
            ]
        )

        for i in range(len(t)):
            writer.writerow(
                [
                    round(t[i], 2),
                    round(gravity_wave[i], 5),
                    round(thermal_wave[i], 5),
                    round(total_signal[i], 5),
                ]
            )

    print(f"\n[Success] High-resolution synodic matrix saved as: '{filename}'")


if __name__ == "__main__":
    run_and_save_lunar_phase()
