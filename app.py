import streamlit as st
import live_telemetry  # Hardware interface for DGPS dongle

# --- STREAMLIT DASHBOARD CONFIGURATION ---
st.set_page_config(
    page_title="Aviation Climate Reporting Models Dashboard",
    page_icon="✈️",
    layout="wide"
)

# Responsive CSS injection
st.markdown("""
<style>
    [data-testid="stSidebar"] { min-width: 200px; max-width: 300px; }
    @media (max-width: 600px) { h1 { font-size: 1.5rem !important; } }
</style>
""", unsafe_allow_html=True)

st.title("✈️ Basic Aviation Knowledge - Airport Reporting Models")
st.markdown("""
This dashboard houses predictive models configured to simulate Climatological Report temperatures ($T_{\text{station}}$) for aviation performance and Density Altitude thresholds. 
*Derived from metrics aligned with the FAA Aviation Weather Handbook.*
""")

# --- GLOBAL TELEMETRY MODE SWITCH ---
st.sidebar.header("📡 Telemetry & Operations Mode")
run_mode = st.sidebar.radio(
    "Select Data Source:",
    ["🗺️ Planning Mode (Static Target)", "✈️ Live Flight Mode (DGPS Dongle)"]
)

# Live Data State Management
live_data = None
if run_mode == "✈️ Live Flight Mode (DGPS Dongle)":
    st.sidebar.success("Live Tracking Engaged. Reading USB Interface...")
    # Change 'COM3' to '/dev/ttyUSB0' for Android/Pydroid if necessary
    live_data = live_telemetry.get_live_position(com_port="/dev/ttyUSB0") 
    
    if live_data["status"] == "SUCCESS":
        st.sidebar.info(f"📍 Lat: {live_data['latitude']:.4f}\n📍 Lon: {live_data['longitude']:.4f}\n🏔️ Alt: {live_data['elevation_ft']} ft\n🛰️ Sats: {live_data['satellites_locked']}")
    else:
        st.sidebar.error("Hardware disconnected or waiting for satellite lock.")

st.sidebar.markdown("---")

# --- NAVIGATION SIDEBAR ---
st.sidebar.header("📁 Navigation & Model Selection")
model_choice = st.sidebar.radio(
    "Choose Atmospheric Model Layer:",
    [
        "San Francisco (SFO / KMUX)",
        "Atlanta Spikes (ATL / KFFC)",
        "Seattle Convergence (SEA / KATX)",
        "Phoenix Thermal Mass (PHX / KIWA)",
        "Chicago Lake Breeze (ORD / KLOT)",
        "Lunar Path & Synodic Log",
        "Planetary Cloud Corridor Engine",
        "12-Month Future Calendar Arc",
        "Cloud Radiative Flux Balance"
    ]
)

# --- MODEL ROUTING ---
# Pass telemetry_override to all modules to enable dynamic flight data

if model_choice == "San Francisco (SFO / KMUX)":
    import sfo_model
    sfo_model.run_sfo_layer(telemetry_override=live_data)

elif model_choice == "Atlanta Spikes (ATL / KFFC)":
    # Routing to your spike-logic module
    import AITA_spikes
    AITA_spikes.run_atl_layer(telemetry_override=live_data)

elif model_choice == "Seattle Convergence (SEA / KATX)":
    import sea_model
    sea_model.run_sea_layer(telemetry_override=live_data)

elif model_choice == "Phoenix Thermal Mass (PHX / KIWA)":
    import phx_model
    phx_model.run_phx_layer(telemetry_override=live_data)

elif model_choice == "Chicago Lake Breeze (ORD / KLOT)":
    import ord_model
    ord_model.run_ord_layer(telemetry_override=live_data)

elif model_choice == "Lunar Path & Synodic Log":
    import lunar_model
    lunar_model.run_lunar_layer()

elif model_choice == "Planetary Cloud Corridor Engine":
    import cloud_model
    cloud_model.run_cloud_layer(telemetry_override=live_data)

elif model_choice == "12-Month Future Calendar Arc":
    import cloud_calendar
    cloud_calendar.run_calendar_arc_layer()

elif model_choice == "Cloud Radiative Flux Balance":
    import radiation_model
    radiation_model.run_radiation_layer()
