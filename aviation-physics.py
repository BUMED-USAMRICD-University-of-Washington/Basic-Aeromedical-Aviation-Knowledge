import streamlit as st
import math

def calculate_ground_effect_ratio(telemetry_override=None, height, wingspan):
    if wingspan <= 0: return 1.0
    h_b_ratio = height / wingspan
    ratio = (33 * (h_b_ratio ** 2)) / (1 + 33 * (h_b_ratio ** 2))
    return ratio

def calculate_crab_angle(wind_speed, wind_dir, runway_heading, tas):
    alpha_rad = math.radians(wind_dir - runway_heading)
    v_crosswind = wind_speed * math.sin(alpha_rad)
    if tas <= abs(v_crosswind): return 0.0, v_crosswind
    theta_deg = math.degrees(math.asin(v_crosswind / tas))
    return theta_deg, v_crosswind

def run_physics_layer():
    st.header("✈️ Aviation Physics & Dynamics Engine")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Ground Effect Calculator")
        h = st.number_input("Height above runway (ft)", 5.0, 50.0, 10.0)
        b = st.number_input("Wingspan (ft)", 20.0, 100.0, 36.0)
        ratio = calculate_ground_effect_ratio(h, b)
        st.write(f"Induced drag is reduced to **{ratio:.1%}** of free-flight values.")
        
    with col2:
        st.subheader("Crab Angle (Wind Correction)")
        w_spd = st.slider("Wind Speed (kts)", 0, 40, 15)
        w_dir = st.slider("Wind Direction (°)", 0, 360, 130)
        rw_hdg = st.number_input("Runway Heading (°)", 0, 360, 90)
        tas = st.number_input("True Airspeed (kts)", 50, 200, 85)
        
        angle, xwind = calculate_crab_angle(w_spd, w_dir, rw_hdg, tas)
        direction = "Right" if angle > 0 else "Left"
        st.write(f"Crosswind: {abs(xwind):.1f} kts")
        st.success(f"Recommended Crab: {abs(angle):.1f}° {direction}")

if __name__ == "__main__":
    run_physics_layer()
