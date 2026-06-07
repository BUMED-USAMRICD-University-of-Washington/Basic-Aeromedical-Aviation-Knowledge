import streamlit as st
import live_telemetry
import ai_pirep

# --- CONFIGURATION ---
st.set_page_config(page_title="Basic Aviation Knowledge", layout="wide")

st.title("✈️ Basic Aviation Knowledge - Master Control")

# --- GLOBAL TELEMETRY ---
# ... (Keep your existing Telemetry Logic here) ...
live_data = None 
# ... 

# --- MODEL SELECTION ---
# This list now includes every identified potential "runnable" module
model_choice = st.sidebar.selectbox("Choose Atmospheric Model Layer:", [
    "Atlanta Spikes (AITA)",
    "Atlanta Heat (AITA Model)",
    "San Francisco (SFO Climate)",
    "Seattle (SEA Convergence)",
    "Phoenix (PHX Thermal)",
    "Chicago (ORD Lake Breeze)",
    "Rossby Wave Dynamics",
    "Lunar Path & Synodic Log",
    "Fog Thermodynamics",
    "Cloud Radiative Flux Balance",
    "Cloud Temperature Drop",
    "Structural Aircraft Icing Hazard Matrix",
    "Wind Dynamics Matrix",
    "Space Weather Engine"
])

# --- MASTER ROUTING TABLE ---
# Helper modules (like aviation_physics) are NOT here; 
# they are imported INSIDE the models below.

if model_choice == "Atlanta Spikes (AITA)":
    import AITA_spikes
    AITA_spikes.run_atl_layer(telemetry_override=live_data)

elif model_choice == "Atlanta Heat (AITA Model)":
    import aita_model
    aita_model.run_atl_layer(telemetry_override=live_data)

elif model_choice == "San Francisco (SFO Climate)":
    import sfo_model
    sfo_model.run_sfo_layer(telemetry_override=live_data)

elif model_choice == "Seattle (SEA Convergence)":
    import sea_model
    sea_model.run_sea_layer(telemetry_override=live_data)

elif model_choice == "Phoenix (PHX Thermal)":
    import phx_model
    phx_model.run_phx_layer(telemetry_override=live_data)

elif model_choice == "Chicago (ORD Lake Breeze)":
    import ord_model
    ord_model.run_ord_layer(telemetry_override=live_data)

elif model_choice == "Rossby Wave Dynamics":
    import rossby_model
    rossby_model.run_rossby_layer(telemetry_override=live_data)

elif model_choice == "Lunar Path & Synodic Log":
    import lunar_model
    lunar_model.run_lunar_layer()

elif model_choice == "Fog Thermodynamics":
    import fog_thermodynamics
    fog_thermodynamics.run_fog_layer(telemetry_override=live_data)

elif model_choice == "Cloud Radiative Flux Balance":
    import radiation_model
    radiation_model.run_radiation_layer(telemetry_override=live_data)

elif model_choice == "Cloud Temperature Drop":
    import cloud_temperature_drop
    cloud_temperature_drop.run_cloud_temp_layer(telemetry_override=live_data)

elif model_choice == "Structural Aircraft Icing Hazard Matrix":
    import aviation_icing
    aviation_icing.run_icing_matrix(telemetry_override=live_data)

elif model_choice == "Wind Dynamics Matrix":
    import wind_dynamics
    wind_dynamics.run_wind_layer(telemetry_override=live_data)

elif model_choice == "Space Weather Engine":
    import space_weather_engine
    space_weather_engine.run_space_layer()
