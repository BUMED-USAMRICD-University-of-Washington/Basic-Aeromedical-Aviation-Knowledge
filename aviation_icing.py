import numpy as np

def calculate_icing_accretion(temp_c, rh_pct, rainfall_mm_hr, elevation_m, wind_mph=30.0):
    """Solves the coupled mass collection and thermodynamic freezing equations."""
    # 1. Core Physical Constants
    L_f = 3.34e5  # Latent heat of fusion for water (J/kg)
    
    # 2. Elevation Pressure Shift Correction
    P_pascals = 101325.0 * (1.0 - 2.25577e-5 * elevation_m) ** 5.25588

    # 3. Derive Airborne Liquid Water Content (LWC)
    if rainfall_mm_hr > 0 and temp_c <= 2.0:
        lwc_g_m3 = 0.072 * (rainfall_mm_hr**0.88)
    else:
        lwc_g_m3 = 0.0

    v_m_s = wind_mph * 0.44704
    lwc_kg_m3 = lwc_g_m3 / 1000.0

    # 4. Thermodynamic Freezing Fraction Matrix
    if temp_c < 0.0 and lwc_g_m3 > 0.0:
        q_evap_loss = (1.0 - rh_pct) * 15.0
        q_convective_loss = 12.5 * np.sqrt(v_m_s) * (0.0 - temp_c)
        total_cooling_energy = q_convective_loss + q_evap_loss
        latent_heat_available = lwc_kg_m3 * v_m_s * L_f
        n_freezing = total_cooling_energy / latent_heat_available
        n_freezing = max(0.0, min(1.0, n_freezing))
    else:
        n_freezing = 0.0

    # 5. Mass Collection Accumulation
    e_collection = 0.65 if temp_c <= 0.0 else 0.0
    mass_accretion_rate_sec = e_collection * n_freezing * lwc_kg_m3 * v_m_s
    mass_accretion_hr_kg = mass_accretion_rate_sec * 3600.0

    return P_pascals / 100.0, lwc_g_m3, n_freezing, mass_accretion_hr_kg

def get_live_icing_pirep_data(live_telemetry, env_data):
    """
    Bridge: Takes live telemetry (GPS) and environmental data to 
    output FAA PIREP codes and intensity metrics.
    """
    # Run the physics math using dongle/model data
    _, _, _, mass = calculate_icing_accretion(
        temp_c=env_data['temp_c'],
        rh_pct=env_data['rh_pct'],
        rainfall_mm_hr=env_data['rain_mm_hr'],
        elevation_m=live_telemetry['elevation_ft'] * 0.3048
    )

    # Map physics output to FAA PIREP intensity standards
    if mass < 0.1:
        intensity = "NONE"
    elif mass < 2.0:
        intensity = "LGT"
    elif mass < 5.0:
        intensity = "MOD"
    else:
        intensity = "SEV"

    # Type categorization based on temperature
    icing_type = "RIME" if env_data['temp_c'] < -10 else "CLEAR"
    
    # Return formatted PIREP string segment
    pirep_code = f"{intensity} {icing_type}" if intensity != "NONE" else "NONE"
    
    return pirep_code, mass
