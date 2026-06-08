# --- PRIMARY ENGINE: Space Weather ---
import os
import struct
import pandas as pd
import matplotlib.pyplot as plt
from numba import njit
import multiprocessing as mp

# --- SECONDARY ENGINE DEPENDENCIES ---
import telemetry_link          # NEW: Integrated Centralized Data Bus
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


# space_weather_engine.py
# Tracks astronomical and solar forcing indices to offset city base grids
# AND evaluates Deep Sky Object (DSO) masses and gravitational fields.

@njit(fastmath=True) # fastmath enables hardware-level floating point optimizations
def calculate_astronomical_offsets(solar_flux_f107, galactic_ray_count):
    """
    Calculates the fractional shift in Total Solar Irradiance (TSI)
    and cosmic ionization scaling factor from space gas tracking.
    """
    # Calculates the fractional shift in Total Solar Irradiance (TSI)
    # over the 11-year solar cycle
    delta_tsi_forcing = (solar_flux_f107 / 1361.0) * 0.25
    
    # Calculates cosmic ionization scaling factor from space gas tracking
    cosmic_variance = galactic_ray_count * 1.38e-23
    
    return delta_tsi_forcing, cosmic_variance

@njit(fastmath=True)
def compute_stellar_mass_and_gravity_vectorized(mags_array):
    """
    High-performance vectorized calculation of Stellar Masses using the
    empirical Mass-Luminosity relation (L proportional to M^3.5),
    and a Net Gravitational Field sum calculation.
    """
    G = 6.67430e-11 # Universal Gravitational Constant
    mass_solar_kg = 1.989e30
    
    masses_solar = np.zeros_like(mags_array)
    net_g_field = 0.0
    
    for i in range(len(mags_array)):
        # L/L_sun = 10 ^ (0.4 * (M_sun - M_star)) | Absolute mag of Sun ~ 4.83
        lum_ratio = 10 ** (0.4 * (4.83 - mags_array[i]))
        
        # M = L^(1/3.5)
        mass_s = lum_ratio ** (1/3.5)
        masses_solar[i] = mass_s
        
        # Gravitational field contribution equation: g_net = G * M / R^2
        # Assuming a normalized R distance approximation (e.g. 100 lightyears in meters) for baseline engine testing
        m_kg = mass_s * mass_solar_kg
        r_normalized_m = 9.461e15 * 100.0 
        
        # Summing the scalar field
        net_g_field += (G * m_kg) / (r_normalized_m ** 2)
        
    return masses_solar, net_g_field

def parse_stellarium_catalog(file_path):
    """
    Parses the Stellarium catalog-3.23.dat file.
    Returns a Pandas DataFrame containing the extracted celestial objects.
    """
    if not os.path.exists(file_path):
        return None

    # Method 1: Attempt to read as Tab-Separated Text (TSV) or CSV
    try:
        with open(file_path, 'rb') as f:
            header_check = f.read(4)
            
        if b'\x00' not in header_check:
            df = pd.read_csv(
                file_path, 
                sep='\t',
                comment='#',
                low_memory=False,
                names=["ID", "RA", "Dec", "Type", "Morph_Type", "Mag", "Size_Arcmin", "Orientation", "Name"]
            )
            df = df.dropna(subset=['RA', 'Dec', 'Mag'])
            return df
            
    except Exception:
        pass

    # Method 2: Binary Struct Parsing (Fallback for compiled catalogs)
    objects = []
    with open(file_path, 'rb') as f:
        header_data = f.read(32) 
        record_size = 24 
        while True:
            record = f.read(record_size)
            if not record or len(record) < record_size:
                break
            try:
                unpacked_data = struct.unpack('<iffffi', record)
                objects.append({
                    "ID": unpacked_data[0],
                    "RA": unpacked_data[1],
                    "Dec": unpacked_data[2],
                    "Mag": unpacked_data[3],
                    "Size_Arcmin": unpacked_data[4],
                    "Type": unpacked_data[5]
                })
            except struct.error:
                break

    df = pd.DataFrame(objects)
    return df.dropna(subset=['Mag'])

def run_space_layer(telemetry_override=None):
    """
    Main orchestration function. Extracts live telemetry, runs the high-performance
    physics simulation, and reports the findings directly to the Boeing JSON payload.
    """
    print("🌌 Running Space Weather Engine...")
    
    # 1. Default Space Weather Baseline (Average Solar Day)
    f107_flux = 150.0  # Solar Flux Units (sfu)
    gcr_count = 5000.0 # Galactic Cosmic Ray counts per minute
    
    # 2. Parse incoming live telemetry
    if telemetry_override:
        f107_flux = telemetry_override.get('solar_flux_f107', f107_flux)
        gcr_count = telemetry_override.get('galactic_ray_count', gcr_
