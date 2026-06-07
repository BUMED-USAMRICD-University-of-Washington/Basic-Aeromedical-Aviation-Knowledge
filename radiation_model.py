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

try:
    import cupy as np  # Attempt to use GPU-accelerated array math
    print("🚀 NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np # Fallback to standard CPU math
    print("⚡ Using CPU (NVIDIA acceleration not detected)")

from numba import njit

@njit(fastmath=True) # fastmath enables hardware-level floating point optimizations
def calculate_density_and_cooling(temp_c, wind_mph, relative_humidity=0.50):
    # Your existing pure-math logic here
    T_kelvin = temp_c + 273.15
    # ... rest of your calculations
    return air_density, wind_chill_c, cooling_delta

def run_radiation_layer(telemetry_override=None):
    st.header("☀️ Radiative Energy Balance & Sensor Heat Flux Model")
    st.markdown(r"### Mathematical Core Energy Balance Engine:")
    st.markdown(r"$$Q_{\text{net}} = (1 - \alpha_s) S^{\downarrow} \mathbf{T}_{\text{sw}}(\rho_c) + \left[ \epsilon_a \sigma T_{\text{atm}}^4 + \mathbf{R}_{\text{lw}}^{\downarrow}(\rho_c) \right] - \epsilon_s \sigma T_{\text{surface}}^4$$")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ☁️ Liquid Water Path (Cloud Density Vector)")
        day_lwp = st.slider("Daytime Integrated Cloud Density ($LWP$ in $g/m^2$)", 0.0, 300.0, 120.0, step=5.0)
        night_lwp = st.slider("Nighttime Integrated Cloud Density ($LWP$ in $g/m^2$)", 0.0, 300.0, 180.0, step=5.0)
        
        st.markdown("### 🌍 Surface Background Constraints")
        s_down = st.number_input("Peak Unobstructed Solar Irradiance ($S^{\downarrow}$ in $W/m^2$)", value=800.0)
        albedo = st.slider("Station Surface Albedo ($\alpha_s$ constant)", 0.05, 0.40, 0.18, step=0.01)
        c_s = st.slider("Ground Soil Thermal Heat Capacity ($C_s$ in $J/m^2 \cdot K$)", 10000, 50000, 25000, step=1000)

    with col2:
        # Fixed physical constants
        sigma = 5.670374e-8  # Stefan-Boltzmann constant
        k_sw = 0.015         # Shortwave extinction factor
        k_lw = 0.022         # Longwave absorption factor
        t_surface_k = 298.15 # Surface temperature baseline (25 C in Kelvin)
        t_atm_k = 288.15     # Upper air temperature baseline (15 C in Kelvin)
        epsilon_a = 0.76     # Clear sky atmospheric emissivity
        epsilon_s = 0.95     # Surface grass/dirt emissivity
        
        # 1. Evaluate Daytime Shortwave Filtration: T_sw = exp(-k_sw * LWP)
        t_sw = np.exp(-k_sw * day_lwp)
        solar_absorbed = (1.0 - albedo) * s_down * t_sw
        
        # 2. Evaluate Nighttime Longwave Trapping: R_lw = (1 - exp(-k_lw * LWP)) * sigma * T^4
        clear_sky_downwelling = epsilon_a * sigma * (t_atm_k**4)
        cloud_longwave_enhancement = (1.0 - np.exp(-k_lw * night_lwp)) * sigma * (t_surface_k**4) * 0.2
        total_longwave_down = clear_sky_downwelling + cloud_longwave_enhancement
        
        # 3. Upwelling Longwave Outflux from Earth's Surface
        upwelling_longwave = epsilon_s * sigma * (t_surface_k**4)
        
        # 4. Net Thermodynamic Heat Budget Flux Loops
        q_net_day = solar_absorbed + total_longwave_down - upwelling_longwave
        q_net_night = 0.0 + total_longwave_down - upwelling_longwave  # No solar at night
        
        # 5. Delta T Derivation Vector (Kelvin/Celsius scale shift per hour)
        delta_t_day_hourly = (q_net_day / c_s) * 3600.0
        delta_t_night_hourly = (q_net_night / c_s) * 3600.0
        
        # --- GRAPH GENERATION ENGINE ---
        fig, ax = plt.subplots(figsize=(10, 4.5))
        timesteps = ['Day High (Shortwave Dominated)', 'Night Low (Longwave Dominated)']
        flux_values = [q_net_day, q_net_night]
        colors = ['gold', 'midnightblue']
        
        bars = ax.bar(timesteps, flux_values, color=colors, edgecolor='black', width=0.4)
        ax.axhline(0, color='black', linestyle='-', alpha=0.5)
        ax.set_ylabel("Net Thermal Energy Flux Budget ($W/m^2$)")
        ax.set_title("NWS Sensor Energy Flux Balance Under Active Cloud Constraints")
        ax.grid(True, axis='y', alpha=0.2)
        
        # Overlay numerical flux labels on top of the rendered bars
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2.0, yval + (15 if yval >= 0 else -35), 
                    f"{yval:.1f} W/m²", ha='center', va='center', fontweight='bold')
                    
        st.pyplot(fig)
        
        # --- RENDER STRATEGIC HOURLY PERFORMANCE METRICS ---
        st.markdown("### 📊 Calculated Thermal Rate Shifts at Weather Station")
        m_col1, m_col2 = st.columns(2)
        m_col1.metric("Daytime Suppressed Warming Rate", f"{delta_t_day_hourly:+.2f} °C / hr", help="Net heat addition to ground soil layer during daylight hours.")
        m_col2.metric("Nighttime Trapped Cooling Rate", f"{delta_t_night_hourly:+.2f} °C / hr", help="Rate of temperature drop. Cloud blanket keeps this value close to zero.")
        
        # --- COMPILE DATA MATRIX STRUCTURAL LOG ---
        df_flux = pd.DataFrame({
            "Radiative_Flux_Component": ["Shortwave_Transmission_Fraction", "Absorbed_Solar_Daytime_W_m2", "Total_Downwelling_Longwave_W_m2", "Upwelling_Surface_Outflux_W_m2", "Net_Daytime_Energy_Flux_W_m2", "Net_Nighttime_Energy_Flux_W_m2"],
            "Calculated_Value": [round(t_sw, 4), round(solar_absorbed, 2), round(total_longwave_down, 2), round(upwelling_longwave, 2), round(q_net_day, 2), round(q_net_night, 2)]
        })
        
        # Integrated Spreadsheet Downloader Link
        st.download_button(
            label="💾 Export Cloud Radiative Flux Matrix (.csv)",
            data=df_flux.to_csv(index=False).encode('utf-8'),
            file_name="cloud_radiative_energy_flux_matrix.csv",
            mime="text/csv"
        )
