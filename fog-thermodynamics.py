import numpy as np


def simulate_cooling_with_dynamic_fog(
    lwp_initial, initial_temp_c=25.0, initial_dewpoint_c=12.0, hours=12.0
):
    """Simulates 12 hours of nighttime cooling, dynamically tracking moisture

    saturation to model fog formation and dew point capping loops.
    """
    # 1. Physical & Thermodynamic Constants
    sigma = 5.670374e-8  # Stefan-Boltzmann constant (W/m^2*K^4)
    k_lw = 0.022  # Cloud longwave absorption coefficient
    epsilon_a = 0.76  # Clear sky atmosphere emissivity
    epsilon_s = 0.95  # Earth surface emissivity
    T_atm_k = 285.15  # Upper air temperature baseline (12°C in Kelvin)
    C_s = 30000.0  # Ground soil layer thermal heat capacity (J/m^2*K)
    L_v = 2.501e6  # Latent heat of vaporization for water (J/kg)

    # 2. Time-stepping Constraints (1-minute numerical intervals)
    dt = 60.0
    steps = int((hours * 3600) / dt)

    # 3. Initialize Dynamic Boundary Conditions
    T_surf = initial_temp_c
    T_dew = initial_dewpoint_c
    lwp_active = lwp_initial

    # Tracking metrics for audit logs
    fog_formed_at_step = None
    latent_heat_released_total = 0.0

    # 4. Core Numerical Integration Loop
    for step in range(steps):
        # Convert values to Kelvin for Stefan-Boltzmann calculations
        T_surf_k = T_surf + 273.15

        # DYNAMIC THRESHOLD CHECK: Has the cooling curve hit the saturation limit?
        if T_surf <= T_dew:
            if fog_formed_at_step is None:
                fog_formed_at_step = step * (dt / 3600.0)  # Log hour of formation

            # 🛑 METEOROLOGICAL CAP 1: Force temperature to lock onto dew point
            T_surf = T_dew
            T_surf_k = T_dew + 273.15

            # 💨 METEOROLOGICAL CAP 2: Condense liquid water path directly at ground level
            # Condense 0.15g/m² of water vapor into liquid droplets per minute
            condensation_rate = 0.15
            lwp_active += condensation_rate

            # 🔥 METEOROLOGICAL CAP 3: Release latent heat back into the surface layer
            # Latent Heat = Mass condensed * Latent constant
            latent_heat_flux = (condensation_rate / 1000.0) * L_v / dt  # W/m²
            latent_heat_released_total += latent_heat_flux * dt
        else:
            latent_heat_flux = 0.0

        # 5. Compute Dynamic Downwelling Infrared Flux
        R_clear_down = epsilon_a * sigma * (T_atm_k**4)
        # Emissivity scales up dynamically as liquid water path drops or builds
        cloud_emissivity_factor = 1.0 - np.exp(-k_lw * lwp_active)
        R_cloud_down = cloud_emissivity_factor * sigma * (T_surf_k**4) * 0.22
        total_longwave_down = R_clear_down + R_cloud_down

        # 6. Compute Outwelling Upwelling Flux
        upwelling_longwave_out = epsilon_s * sigma * (T_surf_k**4)

        # 7. Final Net Energy Balance Matrix (including the latent heat mitigation)
        Q_net = total_longwave_down - upwelling_longwave_out + latent_heat_flux

        # Only apply cooling step if we are not actively locked/capped by dew point
        if T_surf > T_dew:
            dT_dt = Q_net / C_s
            T_surf += dT_dt * dt

    total_drop_c = initial_temp_c - T_surf
    return T_surf, total_drop_c, lwp_active, fog_formed_at_step


if __name__ == "__main__":
    print("=================================================================")
    print("      NWS BOUNDARY LAYER SATURATION & FOG ENGINE                 ")
    print("=================================================================")
    print("Simulating a 12-Hour Night starting at 25.0°C (77.0°F)...")
    print("Tracking dew point caps under varying humidity scenarios:\n")

    # Evaluate different atmospheric humidity profiles
    humidity_scenarios = {
        "Dry Air Matrix (Low Dew Point)": {"temp": 25.0, "dew": 2.0, "lwp": 0.0},
        "Humid Air Matrix (High Dew Point)": {
            "temp": 25.0,
            "dew": 16.0,
            "lwp": 0.0,
        },
        "Pre-Existing Overcast Fog Matrix": {
            "temp": 18.0,
            "dew": 17.0,
            "lwp": 150.0,
        },
    }

    # Run Simulation Loop
    for label, params in humidity_scenarios.items():
        final_t, drop_c, final_lwp, fog_hour = simulate_cooling_with_dynamic_fog(
            lwp_initial=params["lwp"],
            initial_temp_c=params["temp"],
            initial_dewpoint_c=params["dew"],
        )

        print(f"📡 Atmospheric Profile: {label}")
        print(f"   -> Setup Constraints: Initial Temp = {params['temp']}°C | Dew Point = {params['dew']}°C")
        print(f"   -> Final Morning Reading:   {final_t:.2f}°C")
        print(f"   -> Net Temperature Drop:    {drop_c:.2f}°C")

        if fog_hour is not None:
            print(f"   -> 🌁 FOG FORMATION STATE:  Triggered at hour {fog_hour:.2f} of the night cycle")
            print(f"   -> Accumulated Liquid Path: {final_lwp:.1f} g/m² (Dense ground fog blanket)")
        else:
            print("   -> 🌁 FOG FORMATION STATE:  Not triggered (Air column remained subsaturated)")
        print("-" * 70)
