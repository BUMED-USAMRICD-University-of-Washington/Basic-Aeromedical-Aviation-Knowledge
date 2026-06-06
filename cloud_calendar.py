import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def run_calendar_arc_layer():
    st.header("📅 12-Month Multi-Scenario Comparative Engine")
    st.markdown(r"Toggle independent IPCC Shared Socioeconomic Pathways (SSPs) on or off to visually compare cloud density paths ($\Delta LWP$) on a single layout.")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 🎛️ Timeline Constraints")
        target_century_year = st.number_input(
            "Select Evaluation Target Year:", 
            min_value=2026, max_value=2126, value=2075, step=1
        )
        
        st.markdown("### 🌲 Regional Forcing Vectors")
        regional_forcing = st.selectbox(
            "Select Regional Boundary Driver Forcing:",
            ["Midwest Agricultural Belt (Summer Stomatal Surge)", 
             "Great Lakes Basin (Winter Convective Instability Engine)", 
             "Standard Continental Background Matrix"]
        )

        # --- THE NEW ON/OFF TOGGLE SWITCHES ---
        st.markdown("### 🏭 Toggle IPCC Tracks On/Off")
        show_ssp1 = st.checkbox("SSP1-2.6 (Green Growth Track)", value=True)
        show_ssp2 = st.checkbox("SSP2-4.5 (Middle of the Road Track)", value=True)
        show_ssp3 = st.checkbox("SSP3-7.0 (Regional Rivalry Track)", value=False)
        show_ssp5 = st.checkbox("SSP5-8.5 (Fossil-Fueled Track)", value=True)
        
    with col2:
        # Build vector array mapping 365 sequential days of the calendar year
        days_in_year = np.arange(1, 366)
        delta_years = target_century_year - 2026
        
        # 1. Extract Shared Multi-Decadal Ocean Matrix Waves
        pdo_index_wave = 5.2 * np.cos((2 * np.pi / 20.0) * target_century_year)
        amo_index_wave = 3.8 * np.sin((2 * np.pi / 70.0) * target_century_year)
        ocean_forcing_constant = pdo_index_wave + amo_index_wave
        
        # 2. Process Shared High-Resolution Regional Boundary Curve Loops
        if regional_forcing == "Midwest Agricultural Belt (Summer Stomatal Surge)":
            seasonal_profile = 15.0 * np.sin((2 * np.pi / 365.0) * (days_in_year - 110))
        elif regional_forcing == "Great Lakes Basin (Winter Convective Instability Engine)":
            seasonal_profile = 18.0 * np.cos((2 * np.pi / 365.0) * days_in_year)
        else:
            seasonal_profile = 4.0 * np.sin((2 * np.pi / 365.0) * days_in_year)

        # --- GRAPH GENERATION BASE ENGINE ---
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.axhline(50.0, color="black", linestyle=":", alpha=0.3, label="Historical Median")
        
        # Comprehensive Master Dataframe tracking for final spreadsheet exports
        df_export = pd.DataFrame({"Day_Of_Year": days_in_year})
        
        # Dictionary configuration defining the underlying mathematical states
        scenarios = [
            ("SSP1-2.6", -0.012, show_ssp1, "forestgreen"),
            ("SSP2-4.5", -0.045, show_ssp2, "darkorange"),
            ("SSP3-7.0", -0.085, show_ssp3, "crimson"),
            ("SSP5-8.5", -0.140, show_ssp5, "purple")
        ]
        
        active_plots_count = 0
        
        # Loop through each scenario, check if it's toggled ON, calculate, and plot
        for name, beta_decay, is_toggled_on, line_color in scenarios:
            if is_toggled_on:
                base_offset = beta_decay * delta_years
                # Sum the core matrix layers dynamically
                modeled_arc = 50.0 + base_offset + ocean_forcing_constant + seasonal_profile
                modeled_arc = np.clip(modeled_arc, 0.0, 100.0)
                
                # Append data stream straight to the line rendering array
                ax.plot(days_in_year, modeled_arc, color=line_color, linewidth=2.5, label=f"Predicted Path: {name}")
                df_export[f"{name}_Density_Pct"] = np.round(modeled_arc, 2)
                active_plots_count += 1
        
        # Configure calendar month markings along the x-axis grid line arrays
        month_days = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
        ax.set_xticks(month_days)
        ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        
        ax.set_title(f"Multi-Track Comparative Cloud Trajectory Matrix (Year {target_century_year})")
        ax.set_xlabel("Calendar Time Steps (Day of Year)")
        ax.set_ylabel("Calculated Cloud Density Metrics (%)")
        ax.grid(True, alpha=0.2, linestyle="--")
        
        if active_plots_count > 0:
            ax.legend(loc="lower left")
            st.pyplot(fig)
            
            # Export Master Spreadsheet Link Configuration Block
            st.download_button(
                label="💾 Download Combined Multi-Track Data Matrix (.csv)",
                data=df_export.to_csv(index=False).encode('utf-8'),
                file_name=f"multi_ssp_cloud_matrix_{target_century_year}.csv",
                mime="text/csv"
            )
        else:
            st.warning("⚠️ All scenario tracks are currently turned off. Please toggle at least one SSP switch on the left panel to execute the mathematical plotting loop.")
