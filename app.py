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
    ["San Francisco (SFO / KMUX)", "Atlanta Spikes (ATL / KFFC)", "Lunar Path & Synodic Log"]
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
if model_choice == "San Francisco (SFO / KMUX)":
    import sf_model
    sf_model.run_sfo_layer()
elif model_choice == "Atlanta Spikes (ATL / KFFC)":
    import atl_model
    atl_model.run_atl_layer()
elif model_choice == "Lunar Path & Synodic Log":
    import lunar_model
    lunar_model.run_lunar_layer()
