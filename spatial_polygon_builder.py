# spatial_polygon_builder.py
# Converts raw ExpertGPS trackpoint text into 2D spatial polygons for NWS targeting

# --- PRIMARY ENGINE: [Model Name] ---
import numpy as np
from numba import njit
@njit(fastmath=True) # fastmath enables hardware-level floating point optimizations
import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point

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

def build_radar_polygon(telemetry_override=None, filepath, station_id):
    """
    Reads the exported ExpertGPS text file and constructs a 2D boundary polygon.
    """
    # 1. Read the tab-separated data
    df = pd.read_csv(filepath, sep='\t')
    
    # 2. Extract just the Longitude (X) and Latitude (Y) columns
    # We drop any missing rows to ensure the polygon closes cleanly
    coords = df[['Longitude', 'Latitude']].dropna().values.tolist()
    
    # 3. Create the mathematical polygon
    radar_boundary = Polygon(coords)
    
    return {
        "station_id": station_id,
        "boundary_polygon": radar_boundary,
        "area_sq_degrees": radar_boundary.area
    }

def check_if_nws_sensor_is_inside(radar_polygon, sensor_lat, sensor_lon):
    """
    Checks if the specific NWS thermometer physically sits inside the jagged radar ring.
    """
    nws_location = Point(sensor_lon, sensor_lat)
    
    if radar_polygon.contains(nws_location):
        return "COVERED: Sensor is inside the horizontal radar footprint."
    else:
        return "BLIND SPOT: Sensor is outside the horizontal radar footprint."

# Example Execution for Salt Lake City (TSLC)
# salt_lake_radar = build_radar_polygon('data.txt', 'TSLC')
# print(check_if_nws_sensor_is_inside(salt_lake_radar['boundary_polygon'], 40.78, -111.97))
