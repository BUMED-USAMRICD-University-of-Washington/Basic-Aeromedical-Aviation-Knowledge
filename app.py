import streamlit as st

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
        "Cloud Radiative Flux Balance",
        "Rossby Wave Planetary Dynamics",
        "Aircraft Takeoff Weight Optimization",
        "Aviation Physics & Dynamics"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📖 Global Variable Mapping Reference")
st.sidebar.markdown(r"""
* $\Delta T_{\text{station}}$: Localized microclimate sensor offset
* $-\vec{V} \cdot \nabla T$: Horizontal Warm Air Advection
* $z_{\text{inv}}$: Height of marine inversion layer
* $H_{\text{tide}}(t)$: Dynamic tidal gauge height
""")

# Route to selected code engine scripts
if model_choice == "San Francisco (SFO)":
    import sfo_model
    sfo_model.run_sfo_layer()
elif model_choice == "Atlanta Spikes (AITA)":
    import aita_model
    aita_model.run_atl_layer()
elif model_choice == "Lunar Path & Synodic Log":
    import lunar_model
    lunar_model.run_lunar_layer()
elif model_choice == "Planetary Cloud Corridor Engine":
    import cloud_model
    cloud_model.run_cloud_layer()
elif model_choice == "12-Month Future Calendar Arc":
    import cloud_calendar
    cloud_calendar.run_calendar_arc_layer()
elif model_choice == "Cloud Radiative Flux Balance":
    import radiation_model
    radiation_model.run_radiation_layer()
elif model_choice == "Rossby Wave Planetary Dynamics":
    import rossby_model
    rossby_model.run_rossby_layer()
elif model_choice == "Aircraft Takeoff Weight Optimization":
    import aircraft_perf
    aircraft_perf.run_performance_layer()
elif model_choice == "Aviation Physics & Dynamics":
    import aviation_physics
    aviation_physics.run_physics_layer()
