# space_weather_engine.py
# Tracks astronomical and solar forcing indices to offset city base grids

def get_astronomical_offsets(solar_flux_f107, galactic_ray_count):
    # Calculates the fractional shift in Total Solar Irradiance (TSI)
    # over the 11-year solar cycle
    delta_tsi_forcing = (solar_flux_f107 / 1361.0) * 0.25
    
    # Calculates cosmic ionization scaling factor from space gas tracking
    cosmic_variance = galactic_ray_count * 1.38e-23
    
    return delta_tsi_forcing + cosmic_variance
