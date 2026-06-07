import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def run_sfo_layer(telemetry_override=None, telemetry_override=None)::
    st.header("🌁 San Francisco (SFO / KMUX Area) Harmonic Superposition Model")
    st.markdown(r"### Equation: $T_{\text{SF}}(t) = T_0 + \alpha_{\text{SF}} \cdot t + \sum A_i \sin\left(\frac{2\pi}{P_i}t + \phi_i\right) + \Delta T_{\text{station}}$")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Model Initialization Constraints")
        start_year = st.number_input("Start Evaluation Year", min_value=1800, max_value=2026, value=1950)
        end_year = st.number_input("End Evaluation Year", min_value=2026, max_value=2126, value=2026)
        
        st.markdown("### Microclimate Boundary Configuration Values")
        delta_t_station = st.slider(r"Sensor Offset Local Constant ($\Delta T_{\text{station}}$ in °C)", -2.0, 2.0, 0.3, step=0.1)
        z_inv = st.slider("Inversion Boundary Height ($z_{\text{inv}}$ in meters)", 100, 1000, 400, step=50)
        
    with col2:
        years = np.arange(start_year, end_year + 1)
        T_0 = 14.0 
        alpha_SF = 0.008 * (400.0 / z_inv) 
        
        base_trend = T_0 + alpha_SF * (years - start_year)
        pdo_cycle = 0.65 * np.sin((2 * np.pi / 55.0) * years + 0.2)
        enso_cycle = 0.45 * np.sin((2 * np.pi / 4.5) * years + 0.7)
        
        np.random.seed(42)
        epsilon = np.random.normal(0, 0.25, len(years))
        T_SF = base_trend + pdo_cycle + enso_cycle + epsilon + delta_t_station
        
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(years, T_SF, label='Modeled SFO Verification Anomaly', color='teal', alpha=0.8)
        ax.plot(years, base_trend, label='Anthropogenic Marine Inversion Base', color='crimson', linestyle='--')
        ax.set_xlabel("Timeline Year Matrix")
        ax.set_ylabel("Reporting Temperature Value (°C)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        st.pyplot(fig)
        
        df_sfo = pd.DataFrame({
            "Year": years,
            "Base_Trend_C": base_trend,
            "PDO_Contribution_C": pdo_cycle,
            "ENSO_Contribution_C": enso_cycle,
            "Station_Offset_Constant": delta_t_station,
            "Composite_Report_T_C": T_SF
        })
        st.download_button(
            label="💾 Download SFO Spreadsheet (.csv)",
            data=df_sfo.to_csv(index=False).encode('utf-8'),
            file_name=f"SFO_report_{start_year}_{end_year}.csv",
            mime="text/csv"
        )
