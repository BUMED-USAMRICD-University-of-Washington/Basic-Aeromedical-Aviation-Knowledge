# sea_model.py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# --- SECONDARY ENGINE DEPENDENCIES ---
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic

def run_sea_layer(telemetry_override=None):
    st.header("🌲 Seattle (SEA / KATX Area) Convergence & Orographic Model")
    st.markdown(r"### Equation: $T_{\text{SEA}}(d) = T_{\text{rural}} + \Delta T_{\text{olympic}} \cdot \Theta(v) - \Delta T_{\text{pscz}} \cdot \Theta(\text{Wind}) + \Delta T_{\text{station}}$")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Microclimate Boundary Configuration")
        delta_t_station = st.slider(r"Sensor Offset Local Constant ($\Delta T_{\text{station}}$ in °C)", -3.0, 1.0, -1.5, step=0.1)
        v_crit = st.slider("Mid-Level Wind Velocity Threshold (m/s)", 5.0, 25.0, 15.0, step=1.0)
        pscz_active = st.checkbox("Puget Sound Convergence Zone Active", value=True)
        
    with col2:
        hours = np.arange(0, 24)
        t_rural = 12.0 + 4.0 * np.sin((np.pi * (hours - 8)) / 12) # Diurnal baseline
        
        # Downsloping warming effect if wind exceeds critical velocity
        olympic_warming = np.where(v_crit > 12.0, 2.5, 0.0) 
        
        # Convergence zone cooling penalty
        convergence_penalty = -3.0 if pscz_active else 0.0
        
        t_final = t_rural + olympic_warming + convergence_penalty + delta_t_station
        
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(hours, t_final, label='Official Climatological Record Target', color='forestgreen', linewidth=2)
        ax.plot(hours, t_rural, label='Pristine Rural Baseline', color='gray', linestyle='--')
        ax.set_xlabel("Hour of Day")
        ax.set_ylabel("Reporting Temperature Value (°C)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        st.pyplot(fig)
