import streamlit as st
import live_telemetry # Import the new hardware script

# --- STREAMLIT DASHBOARD CONFIGURATION ---
st.set_page_config(
    page_title="Aviation Climate Reporting Models Dashboard",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Basic Aviation Knowledge - Airport Reporting Models")
st.markdown("""
This dashboard houses predictive models configured to simulate Climatological Report temperatures ($T_{\\text{station}}$) for aviation performance and Density Altitude thresholds. 
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
    
    # You can change 'COM3' to whatever port your specific dongle uses
    live_data = live_telemetry.get_live_position(com_port="COM3") 
    
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
        "Lunar Path & Synodic Log", 
        "Planetary Cloud Corridor Engine", 
        "12-Month Future Calendar Arc", 
        "Cloud Radiative Flux Balance"
    ]
)

# Route to selected code engine scripts
if model_choice == "San Francisco (SFO / KMUX)":
    import sfo_model
    # Pass the live_data payload into the model so it can bypass manual coordinate entry
    sfo_model.run_sfo_layer(telemetry_override=live_data) 
# ... (rest of your existing routing statements) ...
