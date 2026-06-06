import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def calculate_exact_roll(temp_c, pressure_inhg, headwind_mph, weight_lbs):
    """Core physics subroutine calculating required ground roll distance for a given weight."""
    sigma = 5.670374e-8
    g = 32.174
    
    # 1. Moist Air Density Vector Calculation
    T_kelvin = temp_c + 273.15
    P_pascals = pressure_inhg * 3386.39
    es = 611.2 * np.exp((17.67 * temp_c) / (temp_c + 243.5))
    pv = es * 0.50
    pd = P_pascals - pv
    rho_air = (pd / (287.05 * T_kelvin)) + (pv / (461.495 * T_kelvin))
    rho_slugs = rho_air * 0.00194032

    # 2. Convert wind velocities to kinematic units
    headwind_fps = headwind_mph * 1.46667

    # 3. Aircraft Structural Template Properties (Cessna 172 Baseline)
    wing_surface_area = 174.0 
    c_l_max = 1.4             
    engine_thrust = 600.0     
    mu_friction = 0.02        

    # 4. Process Aerodynamic Liftoff True Airspeed (TAS)
    v_liftoff_tas = np.sqrt((2.0 * weight_lbs) / (rho_slugs * wing_surface_area * c_l_max))
    v_liftoff_groundspeed = v_liftoff_tas - headwind_fps

    # 5. Solve Integrated Net Forces Across Ground Acceleration Sweep
    avg_drag = 0.05 * engine_thrust 
    avg_lift = 0.33 * weight_lbs    
    
    net_force = engine_thrust - avg_drag - (mu_friction * (weight_lbs - avg_lift))
    avg_acceleration = (net_force * g) / weight_lbs

    # Prevent square-root/division errors if tailwinds or weights create negative forces
    if avg_acceleration <= 0 or v_liftoff_groundspeed <= 0:
        return 99999.0, rho_air

    # Kinematics Matrix: Distance = V^2 / 2a
    ground_roll_feet = (v_liftoff_groundspeed ** 2) / (2.0 * avg_acceleration)
    return ground_roll_feet, rho_air


def run_performance_layer():
    st.header("✈️ Dispatch Matrix - Automated Maximum Allowable Takeoff Weight (MATOW)")
    st.markdown(r"### Aerodynamic Inverse Optimization Engine:")
    st.markdown(r"$$\text{Maximize } W \quad \text{Subject to: } S_G(W, \rho_{\text{air}}, V_{\text{headwind}}) \le S_{\text{available}}$$")

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🛣️ Runway Structural Thresholds")
        runway_length = st.number_input("Available Runway Length ($S_{\text{available}}$ in feet)", min_value=500, max_value=12000, value=1200, step=100)
        runway_heading = st.slider("Active Runway Compass Heading (Degrees)", 0, 360, 90, step=10, help="e.g., Heading 090 is Runway 09")
        
        st.markdown("### 🌡️ Microclimate Field Observations")
        temp_c = st.slider("Surface Ambient Temperature (°C)", -10.0, 45.0, 35.0, step=1.0)
        pressure_inhg = st.number_input("Altimeter Setting (Pressure inHg)", min_value=28.0, max_value=31.0, value=29.92, format="%.2f")
        
        st.markdown("### 💨 Live Anemometer Vectors")
        wind_speed = st.slider("Live Wind Velocity (knots/mph)", 0.0, 40.0, 10.0, step=1.0)
        wind_dir = st.slider("Wind Direction Source Angle (Degrees)", 0, 360, 270, step=10)

    with col2:
        # 1. Run Vector Calculus for Runway Alignment
        runway_rad = np.radians(runway_heading)
        wind_rad = np.radians(wind_dir)
        angle_diff = wind_rad - runway_rad
        headwind_mph = wind_speed * np.cos(angle_diff)
        
        # 2. Run Numerical Search Loop to find MATOW
        # Sweep weight spectrum from empty weight (1,600 lbs) to certified maximum capacity limits
        weight_sweep = np.linspace(1400, 3000, 1600)
        matow_lbs = 1400.0
        calculated_roll_at_matow = 0.0
        rho_air_final = 1.225
        
        for w in weight_sweep:
            roll, rho_air_final = calculate_exact_roll(temp_c, pressure_inhg, headwind_mph, w)
            if roll <= runway_length:
                matow_lbs = w  # Weight is safe, shift ceiling up
                calculated_roll_at_matow = roll
            else:
                break  # Weight overshoots runway margin, break loop
                
        # 3. Compile Performance Vector Chart Lines
        visual_weights = np.linspace(1500, 2800, 50)
        rolls = [calculate_exact_roll(temp_c, pressure_inhg, headwind_mph, vw)[0] for vw in visual_weights]
        
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.plot(visual_weights, rolls, color="crimson", linewidth=2.5, label="Required Ground Roll ($S_G$)")
        ax.axhline(runway_length, color="black", linestyle="--", alpha=0.6, label="Available Runway Limit")
        
        if matow_lbs > 1400:
            ax.axvline(matow_lbs, color="forestgreen", linestyle=":", linewidth=2, label=f"MATOW Limit ({int(matow_lbs)} lbs)")
            
        ax.set_title("Aeronautical Weight vs. Required Runway Concrete Footprint")
        ax.set_xlabel("Gross Takeoff Structural Weight (lbs)")
        ax.set_ylabel("Runway Roll Distance Consumed (feet)")
        ax.set_ylim(0, runway_length * 1.5)
        ax.grid(True, alpha=0.2)
        ax.legend()
        st.pyplot(fig)
        
        # 4. --- RENDER CRITICAL AVIATION DISPATCH FLIGHT METRICS ---
        st.markdown("### 🧮 Dispatch Optimization Metrics")
        m_col1, m_col2 = st.columns(2)
        
        # Flag structural safety warnings based on numerical boundaries
        if matow_lbs >= 2400:
            safety_status = "🟢 FULL STRUCTURAL CAPACITY SAFE FOR DEPARTURE"
            color_mode = "normal"
        elif matow_lbs > 1600:
            safety_status = "⚠️ PAYLOAD REDUCTION REQUIRED: STRIP CARGO/FUEL"
            color_mode = "inverse"
        else:
            safety_status = "🚫 GROUND ROLL OUT OF BOUNDS: FLIGHT GROUNDED"
            color_mode = "off"
            
        m_col1.metric("Maximum Allowable Weight (MATOW)", f"{int(matow_lbs)} lbs", f"Air Density: {rho_air_final:.3f} kg/m³")
        m_col2.metric("Projected Operational Roll", f"{int(calculated_roll_at_matow)} feet", f"Wind Component: {headwind_mph:+.1f} mph")
        st.info(f"**Runway Dispatch Directive:** {safety_status}")
        
        # 5. --- SPREADSHEET MATRIX LOG ---
        df_perf = pd.DataFrame({
            "Performance_Parameter": ["Calculated_Air_Density_kg_m3", "Runway_Headwind_Component_mph", "Available_Concrete_Limit_feet", "Computed_Maximum_Allowable_Weight_lbs", "Ground_Roll_At_MATOW_Limit_feet"],
            "Value": [round(rho_air_final, 4), round(headwind_mph, 1), runway_length, int(matow_lbs), int(calculated_roll_at_matow)]
        })
        
        st.download_button(
            label="💾 Export Weight Optimization Spreadsheet (.csv)",
            data=df_perf.to_csv(index=False).encode('utf-8'),
            file_name=f"runway_weight_optimization_matrix_{int(runway_heading)}.csv",
            mime="text/csv"
        )
