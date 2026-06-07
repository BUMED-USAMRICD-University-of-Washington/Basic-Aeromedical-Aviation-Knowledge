# --- PRIMARY ENGINE: [Model Name] ---
import numpy as np
import pandas as pd
import csv
import matplotlib.pyplot as plt
from datetime import datetime

# --- SECONDARY ENGINE DEPENDENCIES ---
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic
import streamlit as st

def simulate_and_save_sf_climate(telemetry_override=None):
    print("--- SF Climate Superposition Spreadsheet Engine ---")
    start_year = int(input("Enter starting year (e.g., 1850): "))
    end_year = int(input("Enter ending year (e.g., 2026): "))

    t = np.arange(start_year, end_year + 1)

    T_0 = 14.0
    alpha_SF = 0.008

    A_1, P_1, phi_1 = 0.65, 55.0, 0.2
    A_2, P_2, phi_2 = 0.45, 4.5, 0.7
    A_3, P_3, phi_3 = 0.15, 11.0, 0.0

    base_trend = T_0 + alpha_SF * (t - start_year)
    pdo_cycle = A_1 * np.sin((2 * np.pi / P_1) * t + phi_1)
    enso_cycle = A_2 * np.sin((2 * np.pi / P_2) * t + phi_2)
    solar_cycle = A_3 * np.sin((2 * np.pi / P_3) * t + phi_3)

    np.random.seed(42)
    epsilon = np.random.normal(0, 0.25, len(t))
    T_SF = base_trend + pdo_cycle + enso_cycle + solar_cycle + epsilon

    # Generate spreadsheet filename
    filename = f"sf_climate_simulation_{start_year}_{end_year}.csv"

    # Write data vectors sequentially to rows
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        # Spreadsheet headers
        writer.writerow(
            [
                "Year",
                "Anthropogenic_Base_Trend_C",
                "PDO_Cycle_Contribution_C",
                "ENSO_Cycle_Contribution_C",
                "Solar_Cycle_Contribution_C",
                "Stochastic_Noise_C",
                "Total_Composite_Temperature_C",
            ]
        )

        for i in range(len(t)):
            writer.writerow(
                [
                    t[i],
                    round(base_trend[i], 4),
                    round(pdo_cycle[i], 4),
                    round(enso_cycle[i], 4),
                    round(solar_cycle[i], 4),
                    round(epsilon[i], 4),
                    round(T_SF[i], 4),
                ]
            )

    print(f"\n[Success] Raw calculation metrics exported to: '{filename}'")


if __name__ == "__main__":
    simulate_and_save_sf_climate()
