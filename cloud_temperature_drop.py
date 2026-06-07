import numpy as np


def simulate_nocturnal_cooling(telemetry_override=None, lwp_g_m2, initial_temp_c=25.0, hours=12.0):
    """Simulates 12 hours of nighttime radiative cooling by solving the

    Stefan-Boltzmann surface boundary layer energy equations.
    """
    # 1. Standard Physical Constants & Boundary Parameters
    sigma = 5.670374e-8  # Stefan-Boltzmann constant (W/m^2*K^4)
    k_lw = 0.022  # Longwave absorption coefficient for clouds
    epsilon_a = 0.76  # Emissivity of a clear sky atmosphere
    epsilon_s = 0.95  # Emissivity of the earth's surface (grass/soil)
    T_atm_k = 285.15  # Upper-air temperature baseline (12°C in Kelvin)
    C_s = 30000.0  # Soil layer thermal heat capacity (J/m^2*K)

    # 2. Time-stepping Constraints (Numerical Integration Settings)
    dt = 60.0  # Time step of 1 minute (60 seconds)
    total_seconds = int(hours * 3600)
    steps = int(total_seconds / dt)

    # 3. Initialize Dynamic State Arrays
    T_surface_k = initial_temp_c + 273.15  # Convert starting temp to Kelvin

    # 4. Compute Static Downwelling Cloud Flux Component
    # Clear sky contribution
    R_clear_down = epsilon_a * sigma * (T_atm_k**4)
    # Cloud greenhouse trapping modifier: (1 - exp(-k_lw * LWP))
    cloud_emissivity_factor = 1.0 - np.exp(-k_lw * lwp_g_m2)
    R_cloud_down = cloud_emissivity_factor * sigma * (T_surface_k**4) * 0.22

    # Combined total incoming longwave radiation
    total_longwave_down = R_clear_down + R_cloud_down

    # 5. Core Loop: Run Euler Numerical Integration Across the Night
    for step in range(steps):
        # Calculate outgoing upwelling thermal radiation from the ground
        upwelling_longwave_out = epsilon_s * sigma * (T_surface_k**4)

        # Net Energy Balance Equation (No solar influx at night)
        Q_net = total_longwave_down - upwelling_longwave_out

        # Temperature tendency derivation step: dT/dt = Q_net / C_s
        dT_dt = Q_net / C_s

        # Apply time-step increment to current state variable
        T_surface_k += dT_dt * dt

    # Convert final temperature calculation back to Celsius
    final_temp_c = T_surface_k - 273.15
    total_drop_c = initial_temp_c - final_temp_c

    return final_temp_c, total_drop_c, total_longwave_down


if __name__ == "__main__":
    print("=================================================================")
    print("      NWS SENSOR STEFAN-BOLTZMANN BOUNDARY SIMULATOR             ")
    print("=================================================================")
    print("Simulating a 12-Hour Night starting at 25.0°C (77.0°F)...")
    print("Evaluating the exact degree drop across varying cloud states:\n")

    # Define variable cloud profiles to compare (Liquid Water Path in g/m²)
    cloud_test_scenarios = {
        "0.0 (Pristine Clear Sky)": 0.0,
        "25.0 (Thin Translucent Cirrus)": 25.0,
        "100.0 (Moderate Altostratus Deck)": 100.0,
        "250.0 (Dense Low Stratus Blanket)": 250.0,
    }

    # Execute simulation grid loops
    for label, lwp in cloud_test_scenarios.items():
        final_t, degree_drop, lw_flux = simulate_nocturnal_cooling(
            lwp_g_m2=lwp
        )

        # Convert metrics to Fahrenheit for standard NWS verification scales
        initial_f = 77.0
        final_f = (final_t * 9.0 / 5.0) + 32.0
        drop_f = initial_f - final_f

        print(f"☁️  Cloud Liquid Water Path Profile: {label}")
        print(f"   -> Downwelling Longwave Counter-Flux: {lw_flux:.2f} W/m²")
        print(f"   -> Final Morning Sensor Reading:     {final_t:.2f}°C ({final_f:.1f}°F)")
        print(f"   -> EXACT RADIATIVE TEMPERATURE DROP:  {degree_drop:.2f}°C ({drop_f:.1f}°F)")
        print("-" * 65)
