# --- PRIMARY ENGINE: Rossby Wave Dynamics ---
import multiprocessing as mp
import numpy as np # Fallback to standard CPU math
import pandas as pd
import matplotlib.pyplot as plt

# --- SECONDARY ENGINE DEPENDENCIES ---
import telemetry_link          # NEW: Integrated Centralized Data Bus
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic
import streamlit as st
from numba import njit

try:
    import cupy as np  # Attempt to use GPU-accelerated array math
    print("🚀 NVIDIA GPU Acceleration Engaged")
except ImportError:
    print("⚡ Using CPU (NVIDIA acceleration not detected)")


@njit(fastmath=True)
def calculate_rossby_kinematics(u_zonal, station_lat_deg, wave_number, is_zonal_regime):
    """
    Core Mathematical Engine: Highly optimized C-compiled solver for 
    Planetary Beta gradients and wave phase speeds.
    """
    omega = 7.292115e-5    # Earth's angular velocity rotation rate (rad/s)
    r_earth = 6378137.0    # Earth's equatorial radius (meters)
    
    # Convert latitude to radians
    lat_rad = station_lat_deg * (np.pi / 180.0)
    
    # 1. Compute Planetary Beta Factor (Coriolis Parameter Gradient)
    beta_planetary = (2.0 * omega * np.cos(lat_rad)) / r_earth
    
    # 2. Compute Zonal Wavelength and Wave Numbers
    latitude_circumference = 2.0 * np.pi * r_earth * np.cos(lat_rad)
    wavelength_x = latitude_circumference / wave_number
    k_x = (2.0 * np.pi) / wavelength_x
    
    # Set meridional wave spacing scale (~4500 km)
    k_y = (2.0 * np.pi) / 4500000.0
    
    # 3. Dynamic Ocean Matrix Adjustments to Background Wind Speed
    if is_zonal_regime:
        u_adjusted = u_zonal + 6.5
    else:
        u_adjusted = max(5.0, u_zonal - 8.0)
        
    # 4. Solve the Rossby Phase Speed Relation: c = U - beta / (kx^2 + ky^2)
    denominator = (k_x**2) + (k_y**2)
    phase_speed_c = u_adjusted - (beta_planetary / denominator)
    
    # Convert phase speed into cross-country progression metrics (km / day)
    progression_rate_km_day = phase_speed_c * 3.6 * 24.0
    
    return beta_planetary, wavelength_x, u_adjusted, phase_speed_c, progression_rate_km_day


def run_rossby_layer(telemetry_override=None):
    """
    Main orchestration function. Extracts live telemetry, runs the high-performance
    physics simulation, and reports the findings directly to the Boeing JSON payload.
    """
    print("🌊 Running Rossby Wave Phase Speed Matrix...")
    
    # --- 1. HEADLESS BOEING JSON EXPORT ROUTE (CLI) ---
    if telemetry_override is not None:
        u_zonal = 35.0  # Base upper-level wind
        station_lat = telemetry_override.get('lat', 40.0)
        wave_number = 4
        
        # Use the PDO index from telemetry to determine if we are in a zonal regime
        pdo_val = telemetry_override.get('pdo_index', 1.2)
        is_zonal = pdo_val > 0 
        
        beta, wave_x, u_adj, phase_c, prog_rate = calculate_rossby_kinematics(
            u_zonal, station_lat, wave_number, is_zonal
        )
        
        payload = {
            "station_latitude_deg": float(station_lat),
            "planetary_beta_gradient": float(beta),
            "zonal_wavelength_km": float(wave_x / 1000.0),
            "adjusted_jet_core_m_s": float(u_adj),
            "wave_phase_speed_m_s": float(phase_c),
            "migration_rate_km_day": float(prog_rate),
            "is_blocking_pattern": bool(abs(phase_c) < 1.5)
        }
        
        telemetry_link.update_global_state("atmospheric_models", "rossby_wave_index", payload)
        print("✅ Rossby layer calculations reported to global state (Headless).")
        return payload

    # --- 2. STREAMLIT UI ROUTE ---
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
        is_zonal = (ocean_regime == "Warm Pacific / Cool Atlantic (PDO+ / AMO-)")
        
        # Execute decoupled mathematical solver
        beta_planetary, wavelength_x, u_adjusted, phase_speed_c, progression_rate_km_day = calculate_rossby_kinematics(
            u_zonal, station_lat, wave_number, is_zonal
        )
        
        regime_label = "Zonal Cloud Highway" if is_zonal else "Meridional Extreme Block"
        line_style = "-" if is_zonal else "--"
        line_color = "dodgerblue" if is_zonal else "darkviolet"
        
        # --- GENERATE MATHEMATICAL STREAMLINE ARC VISUALIZATION ---
        fig, ax = plt.subplots(figsize=(10, 4.5))
        x_distance_km = np.linspace(0, 4500, 500)
        
        if is_zonal:
            amplitude_y = 150.0  # Tight flat waves
            wave_profile_y = station_lat + (amplitude_y / 111.0) * np.sin((2.0 * np.pi / 4500.0) * wave_number * x_distance_km)
        else:
            amplitude_y = 550.0  # Deep looping trough lines
            wave_profile_y = station_lat + (amplitude_y / 111.0) * np.sin((2.0 * np.pi / 4500.0) * (wave_number - 1) * x_distance_km - 0.5)
            
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
        
        if abs(phase_speed_c) < 1.5:
            status_text = "🔒 STATIONARY ATMOSPHERIC BLOCKING LOCK"
        elif phase_speed_c < 0:
            status_text = "🔄 RETROGRADE WAVE MOVEMENT (WESTWARD)"
        else:
            status_text = "⏩ PROGRESSIVE WEST-TO-EAST HIGHWAY TRANSPORT"
            
        m_col1.metric("Calculated Wave Phase Speed ($c$)", f"{phase_speed_c:.2f} m/s", f"{progression_rate_km_day:+.1f} km/day")
        m_col2.info(f"**Aviation Routing Envelope:** {status_text}")
        
        # --- UPDATE BOEING GLOBAL STATE FROM UI ---
        payload = {
            "station_latitude_deg": float(station_lat),
            "planetary_beta_gradient": float(beta_planetary),
            "zonal_wavelength_km": float(wavelength_x / 1000.0),
            "adjusted_jet_core_m_s": float(u_adjusted),
            "wave_phase_speed_m_s": float(phase_speed_c),
            "migration_rate_km_day": float(progression_rate_km_day),
            "is_blocking_pattern": bool(abs(phase_speed_c) < 1.5)
        }
        telemetry_link.update_global_state("atmospheric_models", "rossby_wave_index", payload)
        
        # --- EXPORT MATRIX LOG ---
        df_rossby = pd.DataFrame({
            "Planetary_Wave_Parameter": ["Target_Latitude_Deg", "Planetary_Beta_Gradient_m_s", "Zonal_Wavelength_km", "Adjusted_Jet_Core_Speed_m_s", "Calculated_Wave_Phase_Speed_m_s", "Cross_Country_Migration_km_day"],
            "Calculated_Value": [round(station_lat, 4), f"{beta_planetary:.4e}", round(wavelength_x / 1000.0, 1), round(u_adjusted, 2), round(phase_speed_c, 2), round(progression_rate_km_day, 1)]
        })
        
        st.download_button(
            label="💾 Export Rossby Wave Steering Matrix Layout (.csv)",
            data=df_rossby.to_csv(index=False).encode('utf-8'),
            file_name=f"rossby_wave_planetary_steering_matrix_{station_lat}N.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    # Local headless test
    print("================================================================")
    print("         ROSSBY WAVE PLANETARY STEERING MATRIX                  ")
    print("================================================================")
    result = run_rossby_layer(telemetry_override={"lat": 47.6062, "pdo_index": 1.5})
    print("\n--- TEST RESULTS ---")
    print(f"Phase Speed: {result['wave_phase_speed_m_s']} m/s")
    print(f"Migration:   {result['migration_rate_km_day']} km/day")
