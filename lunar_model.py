# --- PRIMARY ENGINE: [Model Name] ---
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import astropy.coordinates as coord
import astropy.units as u
from astropy.time import Time

# --- SECONDARY ENGINE DEPENDENCIES ---
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic
import streamlit as st

def run_lunar_layer(telemetry_override=None):
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
                base_time = datetime(int(target_year), 6, 6, 0, 0, 0)
                time_steps = [base_time + timedelta(hours=i) for i in range(48)]
                
                observer_loc = coord.EarthLocation(lat=user_lat*u.deg, lon=user_lon*u.deg, height=user_elev*u.m)
                astropy_times = Time(time_steps)
                alt_az_frame = coord.AltAz(obstime=astropy_times, location=observer_loc)
                
                moon_coords = coord.get_moon(astropy_times).transform_to(alt_az_frame)
                alts = moon_coords.alt.deg
                azs = moon_coords.az.deg
                
                fig_luna, ax_luna = plt.subplots(figsize=(10, 4))
                ax_luna.plot([t.strftime('%H:%M') for t in time_steps], alts, color='indigo', linewidth=2)
                ax_luna.axhline(0, color='black', linestyle=':', alpha=0.5, label='Local Horizon')
                ax_luna.set_ylabel("Altitude Angle (Degrees)")
                ax_luna.set_xlabel("Timeline Steps (Hourly UTC Window)")
                ax_luna.set_title("Predicted Lunar Elevation Profile")
                plt.xticks(rotation=45)
                st.pyplot(fig_luna)
                
                df_luna = pd.DataFrame({
                    "Timestamp_UTC": [t.strftime('%Y-%m-%d %H:%M:%S') for t in time_steps],
                    "Topocentric_Altitude_Deg": alts,
                    "Topocentric_Azimuth_Deg": azs
                })
                st.download_button(
                    label="💾 Download Lunar Log (.csv)",
                    data=df_luna.to_csv(index=False).encode('utf-8'),
                    file_name=f"lunar_log_{target_year}.csv",
                    mime="text/csv"
                )
        else:
            st.info("Click the trigger button above to fire up the Astropy engine.")
