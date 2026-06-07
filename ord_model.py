# --- PRIMARY ENGINE: [Model Name] ---
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# --- SECONDARY ENGINE DEPENDENCIES ---
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic

def run_ord_layer(telemetry_override=None):
    st.header("🌊 Chicago (ORD / KLOT Area) Lake Breeze Frontal Boundary")
    st.markdown(r"### Equation: $T_{\text{ORD}}(x) = T_{\text{continental}} - \left[ \Delta T_{\text{lake}} \cdot \Theta(\Delta P) \cdot \exp\left(-\frac{x}{\lambda_{\text{lake}}}\right) \right]$")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Lake Boundary Variables")
        x_distance = st.slider("Target Distance Inland from Lake (Miles)", 0.5, 30.0, 13.5, step=0.5)
        delta_t_lake = st.slider("Lake/Land Thermal Gradient (°C)", 2.0, 12.0, 8.0, step=0.5)
        front_passed = st.checkbox("Lake Breeze Front Penetration", value=True)
        
    with col2:
        distances = np.linspace(0, 30, 100)
        t_continental = 30.0 # Hot summer day inland
        lambda_lake = 5.0 # Decay rate of the cool breeze moving inland
        
        if front_passed:
            t_profile = t_continental - (delta_t_lake * np.exp(-distances / lambda_lake))
        else:
            t_profile = np.full_like(distances, t_continental)
            
        t_final_target = np.interp(x_distance, distances, t_profile)
        
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(distances, t_profile, label='Temperature Profile', color='royalblue')
        ax.axvline(x=x_distance, color='red', linestyle='--', label=f'Target Coordinates ({t_final_target:.1f}°C)')
        ax.set_xlabel("Distance Inland from Lake Michigan (Miles)")
        ax.set_ylabel("Reporting Temperature Value (°C)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        st.pyplot(fig)
