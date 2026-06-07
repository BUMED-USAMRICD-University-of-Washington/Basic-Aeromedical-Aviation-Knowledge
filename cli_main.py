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

# cli_main.py
import AITA_spikes
import aita_model
import sfo_model

def run_flight_controller(telemetry_override=None):
    print("✈️ Basic Aviation Knowledge - iOS Flight Controller")
    print("Available Engines:")
    print("1. Atlanta Spikes (AITA)")
    print("2. SFO Climate Model")
    # Add your list here...

    choice = input("Enter engine number: ")

    if choice == "1":
        # Pass None or a simulated object for telemetry
        AITA_spikes.run_atl_layer(telemetry_override=None)
    elif choice == "2":
        sfo_model.run_sfo_layer(telemetry_override=None)
    else:
        print("Invalid Engine Selection.")

if __name__ == "__main__":
    run_flight_controller()
