import numpy as np

def calculate_takeoff_roll(telemetry_override=None, temp_c, pressure_inhg, wind_mph, wind_dir_deg, runway_heading_deg, weight_lbs=2400.0):
    """
    Solves the combined moist air density, runway wind vector, and aerodynamic 
    lift equations to predict exact aircraft ground roll distance.
    """
    # --- 1. SOLVE MOIST AIR DENSITY VECTOR ---
    T_kelvin = temp_c + 273.15
    P_pascals = pressure_inhg * 3386.39 # Convert inHg to Pascals
    R_d = 287.05
    # For ground-roll scaling, assume a standard 50% relative humidity baseline
    es = 611.2 * np.exp((17.67 * temp_c) / (temp_c + 243.5))
    pv = es * 0.50
    pd = P_pascals - pv
    rho_air = (pd / (R_d * T_kelvin)) + (pv / (461.495 * T_kelvin))

    # --- 2. SOLVE RUNWAY COMPASS HEADWIND MATRIX ---
    runway_rad = np.radians(runway_heading_deg)
    wind_rad = np.radians(wind_dir_deg)
    angle_diff = wind_rad - runway_rad
    # Convert wind mph to feet per second (fps) for unified kinematic equations
    wind_fps = wind_mph * 1.46667
    headwind_fps = wind_fps * np.cos(angle_diff)

    # --- 3. AIRCRAFT PERFORMANCE TEMPLATE DESIGN (Cessna 172 Baseline) ---
    wing_surface_area = 174.0 # sq ft
    c_l_max = 1.4             # Takeoff flap lift coefficient
    engine_thrust = 600.0     # Static engine thrust force (lbs)
    mu_friction = 0.02        # Dry concrete rolling resistance
    g = 32.174                # Gravity acceleration (ft/s^2)

    # Convert air density from kg/m³ to imperial slugs/ft³ for compatibility
    rho_slugs = rho_air * 0.00194032

    # --- 4. EXECUTE AERODYNAMIC LIFTOFF VELOCITY VALUES ---
    # Calculate True Airspeed (TAS) required for lift generation
    v_liftoff_tas = np.sqrt((2.0 * weight_lbs) / (rho_slugs * wing_surface_area * c_l_max))
    
    # Ground speed at liftoff is True Airspeed minus Headwind component
    v_liftoff_groundspeed = v_liftoff_tas - headwind_fps

    # --- 5. SOLVE INTEGRATED ACCELERATION FOR DISTANCE RUNS ---
    # Average force calculation across the ground roll acceleration sweep
    avg_drag = 0.05 * engine_thrust # Profile drag approximation
    avg_lift = 0.33 * weight_lbs    # Average lift generated prior to rotation
    
    net_accelerating_force = engine_thrust - avg_drag - (mu_friction * (weight_lbs - avg_lift))
    avg_acceleration = (net_accelerating_force * g) / weight_lbs

    # Kinematics Solution: Distance = (V_groundspeed^2) / (2 * Acceleration)
    ground_roll_feet = (v_liftoff_groundspeed ** 2) / (2.0 * avg_acceleration)

    return rho_air, headwind_mph, v_liftoff_tas / 1.46667, ground_roll_feet

if __name__ == "__main__":
    print("================================================================")
    print("      AVIATION DISPATCH FLIGHT PERFORMANCE VECTOR ENGINE        ")
    print("================================================================")
    print("Evaluating Ground Roll Takeoff Matrices for Runway 09 (090°)...")
    print("Aircraft Template: Cessna 172 Standard Profile (2,400 lbs)\n")

    # Parallel Scenarios: Testing the clashing effects of Density vs Wind Shear
    operational_scenarios = {
        "ISA Standard Day (15°C / Clear Sky / Calm)": (15.0, 29.92, 0.0, 0.0),
        "Denver-Style Heat Surge (38°C / Thin Density / Calm)": (38.0, 29.92, 0.0, 0.0),
        "Advection Heat Spike + Tailwind (38°C / Thin Density / 12mph Tailwind from 270°)": (38.0, 29.92, 12.0, 270.0),
    }

    for label, (t, p, w_spd, w_dir) in operational_scenarios.items():
        density, h_wind, tas_liftoff, distance_ft = calculate_takeoff_roll(
            temp_c=t, pressure_inhg=p, wind_mph=w_spd, wind_dir_deg=w_dir, runway_heading_deg=90.0
        )
        
        print(f"✈️  Operational Scenario: {label}")
        print(f"   -> Computed Air Density:        {density:.4f} kg/m³")
        print(f"   -> Active Runway Wind Vector:   {h_wind:+.1f} mph headwind component")
        print(f"   -> Required True Airspeed (TAS): {tas_liftoff:.1f} mph to generate wings-up lift")
        print(f"   -> CRITICAL RUNWAY ROLL DISTANCE: {distance_ft:.1f} FEET OF CONCRETE REQUIRED")
        print("-" * 75)
