from numba import njit

@njit(fastmath=True) # fastmath enables hardware-level floating point optimizations
    
# radar_geometry_parser.py
# Ingests volumetric radar trackpoints to map beam heights over NWS sensors

# --- PRIMARY ENGINE: [Model Name] ---
import io
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

def load_volumetric_radar_data(telemetry_override=None, raw_text_data):
    """
    Parses the raw attribute table containing radar beam heights and trackpoints.
    This creates a 3D profile of the radar coverage for each ICAO station.
    """
    # Read the raw text block into a pandas DataFrame
    df = pd.read_csv(io.StringIO(raw_text_data), sep='\s{2,}', engine='python')
    
    # Clean the column names for programmatic access
    df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
    
    # Dictionary to hold the vertical beam profile for each airport
    radar_profiles = {}
    
    # Group the data by the 4-letter ICAO identifier
    for icao, group in df.groupby('icao'):
        # Sort by height to build the beam from the ground up
        group = group.sort_values(by='height')
        
        radar_profiles[icao] = {
            "total_trackpoints": int(group['number_of_trackpoints'].sum()),
            "beam_type": group['beam'].iloc[0],
            "lowest_scan_height_ft": int(group['height'].min()),
            "highest_scan_height_ft": int(group['height'].max()),
            "volumetric_slices": group[['height', 'number_of_trackpoints']].to_dict(orient='records')
        }
        
    return radar_profiles

def check_sensor_coverage(radar_profile, target_sensor_elevation_ft):
    """
    Determines if the radar's lowest beam overshoots the physical NWS thermometer.
    """
    lowest_beam = radar_profile['lowest_scan_height_ft']
    
    if lowest_beam > target_sensor_elevation_ft:
        return {
            "status": "OVERSHOOT",
            "blind_spot_gap_ft": lowest_beam - target_sensor_elevation_ft,
            "warning": "Radar misses surface microclimate (UHI/Fog)."
        }
    return {"status": "COVERED", "blind_spot_gap_ft": 0}
