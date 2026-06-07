import streamlit as st
import live_telemetry
import ai_pirep
import aviation_icing # Module for ice prediction

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(page_title="Basic Aviation Knowledge Dashboard", layout="wide")

st.title("✈️ Basic Aviation Knowledge - Master Control")

# --- GLOBAL TELEMETRY ---
st.sidebar.header("📡 Telemetry & Operations")
run_mode = st.sidebar.radio("Data Source:", ["🗺️ Planning Mode (Static)", "✈️ Live Flight Mode (DGPS)"])

live_data = None
if run_mode == "✈️ Live Flight Mode (DGPS)":
    live_data = live_telemetry.get_live_position(com_port="/dev/ttyUSB0")
    if live_data["status"] == "SUCCESS":
        st.sidebar.info(f"📍 {live_data['latitude']:.4f}, {live_data['longitude']:.4f} | 🏔️ {live_data['elevation_ft']} ft")
    else:
        st.sidebar.error("Hardware disconnected.")

# --- TOOLS: PIREP SUBMISSION ---
@st.dialog("Submit AI-PIREP")
def submit_pirep_dialog():
    ac_type = st.text_input("Aircraft Type", "C172")
    turbulence = st.selectbox("Turbulence", ["LGT", "MOD", "SEV"])
    icing = st.selectbox("Icing", ["NONE", "LGT RIME", "MOD CLEAR"])
    remarks = st.text_area("Remarks")
    if st.button("Generate & Speak"):
        user_inputs = {"ac_type": ac_type, "turbulence": turbulence, "icing": icing, "remarks": remarks}
        pirep_str, spoken_str = ai_pirep.generate_pirep_data(live_data or {}, user_inputs)
        st.code(pirep_str)
        ai_pirep.speak_pirep(spoken_str)

if st.sidebar.button("🛠️ Tools: Submit AI-PIREP"):
    submit_pirep_dialog()

# --- MODEL SELECTION ---
st.sidebar.header("📁 Model Selection")
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
    "Structural Aircraft Icing Hazard Matrix"
])

# --- MODEL ROUTING ---
# Pass telemetry_override to enable dynamic flight data in all models

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

elif model_choice == "Structural Aircraft Icing Hazard Matrix":
    import aviation_icing
    # Example integration for the icing hazard matrix
    st.header("❄️ Structural Aircraft Icing Hazard Matrix")
    # You can pass live_data to the icing module here
    # aviation_icing.run_icing_matrix(telemetry_override=live_data)
    st.write("Icing Matrix Active.")
