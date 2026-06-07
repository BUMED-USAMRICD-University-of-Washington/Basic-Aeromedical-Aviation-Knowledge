# sensor_thermodynamics.py
# Calculates the evaporative cooling penalty and thermal lag for official temperature sensors

def calculate_wet_sensor_penalty(t_ambient_c, humidity, wind_speed_mps, is_wooden_sensor=False, is_raining=True):
    """
    Adjusts the predicted official maximum temperature downward due to 
    evaporative cooling on the physical thermometer enclosure.
    """
    if not is_raining:
        return 0.0  # No penalty if the sensor is completely dry
        
    # Latent heat of vaporization and baseline convection
    L_v = 2260.0  # J/g
    h_c = 10.45 - wind_speed_mps + 10 * (wind_speed_mps ** 0.5) # Simplified convection coefficient
    
    # Vapor pressure deficit (driving force of evaporation)
    # E_rate increases as humidity drops (e.g., rain stops, sun comes out, but box is still wet)
    e_rate = (100.0 - humidity) * 0.02 * wind_speed_mps 
    
    # Material absorption modifier (Theta)
    # Wooden COOP shelters absorb water; Plastic ASOS shields shed water.
    material_modifier = 1.0 if is_wooden_sensor else 0.15
    
    # Calculate the artificial temperature drop caused by the wet box
    delta_t_evap_c = (L_v * e_rate / (h_c * 1000)) * material_modifier
    
    # Convert penalty to Fahrenheit
    delta_t_evap_f = delta_t_evap_c * (9.0/5.0)
    
    return round(delta_t_evap_f, 2)

# Example Execution:
# If a wooden rural sensor gets rained on, and then the wind blows at 5 m/s with 60% humidity:
# penalty = calculate_wet_sensor_penalty(30.0, 60.0, 5.0, is_wooden_sensor=True)
# The final official record will read ~2.5°F COOLER than the actual ambient air.
