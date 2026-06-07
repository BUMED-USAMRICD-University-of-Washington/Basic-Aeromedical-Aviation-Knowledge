# --- PRIMARY ENGINE: [Model Name] ---
import streamlit as st
import numpy as np
from numba import njit
@njit(fastmath=True) # fastmath enables hardware-level floating point optimizations
import pandas as pd
import matplotlib.pyplot as plt

# --- SECONDARY ENGINE DEPENDENCIES ---
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic

try:
    import cupy as np  # Attempt to use GPU-accelerated array math
    print("🚀 NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np # Fallback to standard CPU math
    print("⚡ Using CPU (NVIDIA acceleration not detected)")
    
def run_rossby_layer(telemetry_override=None):
    st.header("🌊 Rossby Wave Phase Speed & Jet Stream Configuration Engine")
    st.markdown(r"### Mathematical Core Planetary Dynamics Engine:")
    st.markdown(r"$$c = U_{\text{zonal}} - \frac{\beta_{\text{planetary}}}{k_x^2 + k_y^2}$$")
    st.markdown(r"Where $\beta_{\text{planetary}} = \frac{2\Omega \cos(\phi)}{R_E}$ tracks the North-South Coriolis variation across the Earth.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 💨 Upper-Troposphere Wind Forcing")
        u_zonal = st.slider("Mean Background Zonal Wind Speed ($U_{\text{zonal}}$ in m/s)", 10.0, 60.0, 35.0, step=1.0)
        
        st.markdown("### 🗺️ Planetary Scale Constraints")
        station_lat = st.slider("Target Station Latitude ($\phi$ in decimal degrees)", 25.0, 60.0, 40.0, step=1.0)
        wave_number = st.slider("Hemispheric Wave Number ($n$, total waves wrapping Earth)", 2, 8, 4)
        
        st.markdown("### 🌀 Multi-Decadal Ocean Coupling States")
        ocean_regime = st.selectbox(
            "Select Active Decadal Ocean Matrix State:",
            ["Warm Pacific / Cool Atlantic (PDO+ / AMO-)", "Cool Pacific / Warm Atlantic (PDO- / Warm AMO)"]
        )

    with col2:
        # Fixed Planetary Physics Constants
        omega = 7.292115e-5    # Earth's angular velocity rotation rate (rad/s)
        r_earth = 6378137.0    # Earth's equatorial radius (meters)
        
        # Convert user latitude to radians
        lat_rad = np.radians(station_lat)
        
        # 1. Compute Planetary Beta Factor (Coriolis Parameter Gradient)
        beta_planetary = (2.0 * omega * np.cos(lat_rad)) / r_earth
        
        # 2. Compute Zonal Wavelength and Wave Numbers
        # Earth's circumference at selected latitude circle boundary
        latitude_circumference = 2.0 * np.pi * r_earth * np.cos(lat_rad)
        wavelength_x = latitude_circumference / wave_number
        k_x = (2.0 * np.pi) / wavelength_x
        
        # Set meridional wave spacing scale to approximate standard North American landmass width (~4500 km)
        k_y = (2.0 * np.pi) / 4500000.0
        
        # 3. Dynamic Ocean Matrix Adjustments to Background Wind Speed
        if ocean_regime == "Warm Pacific / Cool Atlantic (PDO+ / AMO-)":
            # Direct matrix reinforcement flattens wave loops, tightening jet core velocity
            u_adjusted = u_zonal + 6.5
            regime_label = "Zonal Cloud Highway"
            line_style = "-"
        else:
            # Amplified meridional looping breaks wind speeds into localized shear dips
            u_adjusted = max(5.0, u_zonal - 8.0)
            regime_label = "Meridional Extreme Block"
            line_style = "--"
            
        # 4. Solve the Rossby Phase Speed Relation: c = U - beta / (kx^2 + ky^2)
        denominator = (k_x**2) + (k_y**2)
        phase_speed_c = u_adjusted - (beta_planetary / denominator)
        
        # Convert phase speed into cross-country progression metrics (km / day)
        progression_rate_km_day = phase_speed_c * 3.6 * 24.0
        
        # 5. --- GENERATE MATHEMATICAL STREAMLINE ARC VISUALIZATION ---
        fig, ax = plt.subplots(figsize=(10, 4.5))
        x_distance_km = np.linspace(0, 4500, 500)  # Represent Coast-to-Coast span
        
        # Calculate dynamic wavy path trajectory profile mapping jet stream shape
        if "Zonal" in regime_label:
            amplitude_y = 150.0  # Tight flat waves
            wave_profile_y = station_lat + (amplitude_y / 111.0) * np.sin((2.0 * np.pi / 4500.0) * wave_number * x_distance_km)
            line_color = "dodgerblue"
        else:
            amplitude_y = 550.0  # Deep looping trough lines
            wave_profile_y = station_lat + (amplitude_y / 111.0) * np.sin((2.0 * np.pi / 4500.0) * (wave_number - 1) * x_distance_km - 0.5)
            line_color = "darkviolet"
            
        ax.plot(x_distance_km, wave_profile_y, color=line_color, linestyle=line_style, linewidth=3, label=f"Wind Path Profile ({regime_label})")
        ax.axhline(station_lat, color="black", linestyle=":", alpha=0.4, label="Station Center Target Latitude")
        
        ax.set_title(f"Planetary Jet Stream Wave Core Vector Trajectory Across America")
        ax.set_xlabel("Cross-Country Spatial Vector Distance (km from Pacific Coast)")
        ax.set_ylabel("Geographic Positioning Grid Line (Latitude)")
        ax.grid(True, alpha=0.2)
        ax.legend(loc="upper right")
        st.pyplot(fig)
        
        # --- RENDER STRATEGIC AVIATION PERFORMANCE METRICS ---
        st.markdown("### 📊 Planetary Wave Velocity Matrix Outputs")
        m_col1, m_col2 = st.columns(2)
        
        # Determine wave movement status based on final calculated phase speed metrics
        if abs(phase_speed_c) < 1.5:
            status_text = "🔒 STATIONARY ATMOSPHERIC BLOCKING LOCK"
        elif phase_speed_c < 0:
            status_text = "🔄 RETROGRADE WAVE MOVEMENT (WESTWARD)"
        else:
            status_text = "⏩ PROGRESSIVE WEST-TO-EAST HIGHWAY TRANSPORT"
            
        m_col1.metric("Calculated Wave Phase Speed ($c$)", f"{phase_speed_c:.2f} m / s", f"{progression_rate_km_day:+.1f} km / day")
        m_col2.info(f"**Aviation Routing Envelope:** {status_text}")
        
        # --- COMPILE DATA MATRIX LOG ---
        df_rossby = pd.DataFrame({
            "Planetary_Wave_Parameter": ["Target_Latitude_Radians", "Planetary_Beta_Gradient_m_s", "Zonal_Wavelength_km", "Adjusted_Jet_Core_Speed_m_s", "Calculated_Wave_Phase_Speed_m_s", "Cross_Country_Migration_km_day"],
            "Calculated_Value": [round(lat_rad, 4), f"{beta_planetary:.4e}", round(wavelength_x / 1000.0, 1), round(u_adjusted, 2), round(phase_speed_c, 2), round(progression_rate_km_day, 1)]
        })
        
        st.download_button(
            label="💾 Export Rossby Wave Steering Matrix Layout (.csv)",
            data=df_rossby.to_csv(index=False).encode('utf-8'),
            file_name=f"rossby_wave_planetary_steering_matrix_{station_lat}N.csv",
            mime="text/csv"
        )
