import live_telemetry
from waypoint_manager import WaypointManager
# Initialize the manager globally
wp_manager = WaypointManager()
import ai_pirep
import streamlit as st

# Inside your main application loop
def guidance_loop(aircraft_state, waypoint):
    # 1. Sense acceleration/motion
    accel = get_sensors_accelerometer() 
    current_force = calculate_force_vectors(accel, aircraft_state.mass)
    
    # 2. Recalculate if Dynamic Mode is ON
    if flight_computer.dynamic:
        commands = flight_computer.calculate_required_attitude(
            aircraft_state.heading, 
            waypoint.heading, 
            waypoint.elevation,
            aircraft_state.altitude,
            aircraft_state.ground_speed
        )
        return commands

# Initialize
wp_manager = WaypointManager()
computer = FlightControlDynamics(mode="CIVILIAN")

st.title("✈️ Aviation Knowledge Engine")

# --- WAYPOINT REGISTRATION SIDEBAR ---
with st.sidebar:
    st.header("Waypoint Registration")
    wp_name = st.text_input("Waypoint Name")
    lat = st.number_input("Latitude", value=0.0)
    lon = st.number_input("Longitude", value=0.0)
    alt = st.number_input("Target Altitude", value=1500)
    heading = st.number_input("Target Heading", value=180)
    
    if st.button("Register Waypoint"):
        wp_manager.register_waypoint(wp_name, lat, lon, alt, heading)
        st.success(f"Registered {wp_name}")

# --- DYNAMICS MONITOR ---
st.subheader("Live Trim Correction")
active_wp = wp_manager.get_active_waypoint(index=0)
if active_wp:
    st.write(f"**Navigating to:** {active_wp.name}")
    # Compute correction
    correction = computer.calculate_required_attitude(
        current_heading=170, # Placeholder for live telemetry
        target_heading=active_wp.target_heading,
        target_elevation=active_wp.alt,
        current_alt=1450,
        ground_speed=250
    )
    st.json(correction)
else:
    st.warning("No waypoint active.")
    
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
    
# --- FOOTER & DEDICATIONS ---
st.sidebar.markdown("---")
st.sidebar.caption("Dedicated to the faculty at [Green River College](https://www.greenriver.edu/students/academics/areas-of-interest/program-maps/trades-industrial-tech-aviation-natural-resources/aviation-technology/index.html)")
st.sidebar.caption("Professional Legal Reference: [Fox Rothschild Aviation](https://www.foxrothschild.com/aviation)")
