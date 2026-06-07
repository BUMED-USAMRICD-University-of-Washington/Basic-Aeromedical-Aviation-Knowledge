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

# space_weather_engine.py
# Tracks astronomical and solar forcing indices to offset city base grids

def get_astronomical_offsets(telemetry_override=None, solar_flux_f107, galactic_ray_count):
    # Calculates the fractional shift in Total Solar Irradiance (TSI)
    # over the 11-year solar cycle
    delta_tsi_forcing = (solar_flux_f107 / 1361.0) * 0.25
    
    # Calculates cosmic ionization scaling factor from space gas tracking
    cosmic_variance = galactic_ray_count * 1.38e-23
    
    return delta_tsi_forcing + cosmic_variance
