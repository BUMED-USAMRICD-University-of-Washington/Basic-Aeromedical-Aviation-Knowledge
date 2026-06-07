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

def run_atl_layer(telemetry_override=None):
    st.header("🍑 Atlanta Spikes (ATL / KFFC Area) Local Temperature Tendency")
    st.markdown(r"### Equation: $\frac{\partial T}{\partial t} = -\vec{V} \cdot \nabla T + \left(\frac{\alpha}{c_p}\right)\omega + \frac{J}{c_p}$")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Synoptic Heat Influx Controls")
        base_temp = st.number_input("Forecast Base Model Surface Temperature (°F)", value=81.0)
        heating_duration = st.slider("Afternoon Peak Subsidizing Window (Hours)", 1.0, 8.0, 5.0, step=0.5)
        
        st.markdown(r"### Horizontal Wind Advection ($-\vec{V} \cdot \nabla T$) Constraints")
        wind_speed = st.slider("Southwesterly Inflow Wind Velocity (mph)", 0.0, 30.0, 15.0, step=1.0)
        temp_gradient = st.slider("Thermal Gradient Step Range (°F per 100 miles)", 0.0, 5.0, 2.5, step=0.1)
        
    with col2:
        st.markdown("### Mountain Downslope Compression Properties")
        subsidence = st.slider("Ridge Atmospheric Sinking Air Rate (microbars/sec)", 0.0, 5.0, 2.2, step=0.1)
        solar_clear = st.slider(r"Clear Sky Direct Radiation Scale Factor ($J/c_p$ °F/hr)", 0.5, 3.0, 1.4, step=0.1)
        
        advection_rate = wind_speed * (temp_gradient / 100.0)
        compression_warming = subsidence * 0.45
        total_hourly_tendency = advection_rate + compression_warming + solar_clear
        calculated_peak_target = base_temp + (total_hourly_tendency * heating_duration)
        
        st.markdown("### Final Safety Performance Output Metrics")
        st.metric(label=r"Calculated Verification Peak Temperature ($T_{\text{station}}$)", value=f"{calculated_peak_target:.2f} °F")
        
        df_atl = pd.DataFrame({
            "Parameter Metric Component": ["Advection Rate Inflow", "Dynamic Downslope Compression", "Solar Radiation Vector", "Net Hourly Shift Value", "Final Projected Peak Target"],
            "Calculated Scalar Value": [f"+{advection_rate:.3f} °F/hr", f"+{compression_warming:.3f} °F/hr", f"+{solar_clear:.3f} °F/hr", f"+{total_hourly_tendency:.3f} °F/hr", f"{calculated_peak_target:.2f} °F"]
        })
        st.table(df_atl)
        st.download_button(
            label="💾 Download ATL Report Data (.csv)",
            data=df_atl.to_csv(index=False).encode('utf-8'),
            file_name="ATL_heat_spike_metrics.csv",
            mime="text/csv"
        )
