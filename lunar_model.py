import astropy.coordinates as coord
import astropy.units as u
import multiprocessing as mp
import pandas as pd
import matplotlib.pyplot as plt
import telemetry_link
from telemetry_link import time_manager
import datetime
now = time_manager.get_now()
from astropy.time import Time
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
from datetime import datetime, timedelta

def calculate_future_position():
    # This respects your manual override if you set one!
    now = telemetry_link.time_manager.get_now() 
    future = now + datetime.timedelta(hours=48)
    return future

def calculate_lunar_ephemeris(lat, lon, elev, target_year):
    """Core mathematical solver for lunar topocentric coordinates."""
    base_time = datetime(int(target_year), 6, 6, 0, 0, 0)
    time_steps = [base_time + timedelta(hours=i) for i in range(48)]

    # Configure observer ground station
    observer_loc = coord.EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=elev*u.m)
    astropy_times = Time(time_steps)
    alt_az_frame = coord.AltAz(obstime=astropy_times, location=observer_loc)

    # Compute Ephemeris Matrix
    moon_coords = coord.get_moon(astropy_times).transform_to(alt_az_frame)
    alts = moon_coords.alt.deg
    azs = moon_coords.az.deg

    return time_steps, alts, azs


def run_lunar_layer(telemetry_override=None):
    """
    Main orchestration function. Extracts live telemetry, runs the high-performance
    physics simulation, and reports the findings directly to the Boeing JSON payload.
    """
    print("🌙 Running Celestial Tracking Matrix (Lunar Model)...")
    
    # --- 1. HEADLESS BOEING JSON EXPORT ROUTE ---
    # If telemetry_override is passed (e.g. from cli_main.py), run the math 
    # immediately without waiting for Streamlit UI button clicks.
    if telemetry_override is not None:
        user_lat = telemetry_override.get('lat', 47.6062)
        user_lon = telemetry_override.get('lon', -122.3321)
        user_elev = telemetry_override.get('elevation_m', 45.0)
        target_year = telemetry_override.get('year', 2026)
        
        time_steps, alts, azs = calculate_lunar_ephemeris(user_lat, user_lon, user_elev, target_year)
        
        payload = {
            "station_latitude": float(user_lat),
            "station_longitude": float(user_lon),
            "current_lunar_altitude_deg": round(float(alts[0]), 2),
            "current_lunar_azimuth_deg": round(float(azs[0]), 2),
            "tracking_active": True
        }
        telemetry_link.update_global_state("navigation", "lunar_ephemeris", payload)
        print("✅ Lunar navigation calculations reported to global state.")
        return payload

    # --- 2. STREAMLIT UI ROUTE ---
    st.header("🌙 Celestial Tracking Matrix - Topocentric Lunar Path Generator")
    st.markdown(r"Calculates the topocentric tracking path vectors ($\vec{R}_{\text{topo}}$) relative to custom digital GPS receiver antennas.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Receiver Terminal Coordinates (Decimal GPS)")
        user_lat = st.number_input("Decimal Station Latitude", value=47.6062, format="%.4f")
        user_lon = st.number_input("Decimal Station Longitude", value=-122.3321, format="%.4f")
        user_elev = st.number_input("Antenna Hub Elevation (meters)", value=45.0)
        target_year = st.number_input("Calculated Prediction Year", value=2026, min_value=2020, max_value=2120)
        
    with col2:
        st.markdown("### Astropy Topocentric Orbit Evaluation Loop")
        if st.button("⚡ Run Astropy Ephemeris Numerical Computation Matrix"):
            with st.spinner("Processing 48-Hour Horizon Arc Steps..."):
                
                # Execute decoupled mathematical solver
                time_steps, alts, azs = calculate_lunar_ephemeris(user_lat, user_lon, user_elev, target_year)
                
                # Render Visualization
                fig_luna, ax_luna = plt.subplots(figsize=(10, 4))
                ax_luna.plot([t.strftime('%H:%M') for t in time_steps], alts, color='indigo', linewidth=2)
                ax_luna.axhline(0, color='black', linestyle=':', alpha=0.5, label='Local Horizon')
                ax_luna.set_ylabel("Altitude Angle (Degrees)")
