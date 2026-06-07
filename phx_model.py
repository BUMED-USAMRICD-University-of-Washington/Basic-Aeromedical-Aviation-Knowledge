# phx_model.py
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
    
def run_phx_layer(telemetry_override=None):
    st.header("🏜️ Phoenix (PHX / KIWA Area) Thermal Mass Retention Model")
    st.markdown(r"### Equation: $T_{\text{PHX}}(t) = T_{\text{desert}} + \Delta T_{\text{uhi\_max}} \cdot \left(1 - \exp\left(-\frac{t}{\tau_{\text{thermal}}}\right)\right) + \Delta T_{\text{station}}$")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### UHI & Infrastructure Configuration")
        delta_t_uhi = st.slider("Peak Urban Heat Island Intensity (°C)", 2.0, 8.0, 5.5, step=0.5)
        tau_thermal = st.slider("Asphalt Thermal Decay Constant (Hours)", 1.0, 6.0, 3.2, step=0.1)
        
    with col2:
        hours = np.arange(0, 24)
        # Standard rapid desert cooling at night
        t_desert = 35.0 - 15.0 * np.exp(-hours / 6.0) 
        
        # UHI effect preventing the city from cooling down
        uhi_retention = delta_t_uhi * (1 - np.exp(-hours / tau_thermal))
        
        t_final = t_desert + uhi_retention
        
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(hours, t_final, label='Verified City Baseline (Downtown)', color='darkorange', linewidth=2)
        ax.plot(hours, t_desert, label='Rural Desert Ambient', color='peru', linestyle='--')
        ax.set_xlabel("Hours post-sunset")
        ax.set_ylabel("Reporting Temperature Value (°C)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        st.pyplot(fig)
