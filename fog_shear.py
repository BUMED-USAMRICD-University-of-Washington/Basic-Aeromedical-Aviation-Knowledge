import numpy as np


def simulate_cooling_with_wind_shear(
    lwp_initial,
    initial_temp_c=25.0,
    initial_dewpoint_c=16.0,
    base_wind_mph=5.0,
    gust_frequency=0.05,
    hours=12.0,
):
    """Simulates 12 hours of nighttime cooling, dynamically tracking fog condensation

    balanced against mechanical scattering from wind shear gusts.
    """
    # 1. Physical & Thermodynamic Constants
    sigma = 5.670374e-8  # Stefan-Boltzmann constant (W/m^2*K^4)
    k_lw = 0.022  # Cloud longwave absorption coefficient
    epsilon_a = 0.76  # Clear sky atmosphere emissivity
    epsilon_s = 0.95  # Earth surface emissivity
    T_atm_k = 285.15  # Upper air temperature baseline
    C_s = 30000.0  # Ground soil layer thermal heat capacity (J/m^2*K)
    L_v = 2.501e6  # Latent heat of vaporization for water (J/kg)

    # 2. Critical Mechanical Shear Constants
    CRITICAL_GUST_SHEAR = (
        12.0  # Wind speeds above 12 mph trigger fog scattering
    )

    # 3. Time-stepping Constraints (1-minute intervals)
    dt = 60.0
    steps = int((hours * 3600) / dt)

    # 4. Initialize Dynamic States
    T_surf = initial_temp_c
    T_dew = initial_dewpoint_c
    lwp_active = lwp_initial

    # Tracking counters
    fog_hours_accumulated = 0.0
    total_scatter_events = 0

    # Seed random generator for predictable gust cycles across scenarios
    np.random.seed(101)

    # 5. Numerical Integration Loop
    for step in range(steps):
        T_surf_k = T_surf + 273.15

        # Generate stochastic wind speed profile for this time step
        # Base wind plus random turbulence spikes (gusts)
        current_wind = base_wind_mph + np.random.exponential(
            scale=gust_frequency * 100.0
        )

        # EVALUATE CRITICAL SHEAR LIMITS: Is wind strong enough to strip fog?
        if current_wind >= CRITICAL_GUST_SHEAR and lwp_active > 0:
            # Mechanical wind shear strips away 2.5g/m² of fog density per minute
            shear_scattering_rate = 2.5
            lwp_active = max(0.0, lwp_active - shear_scattering_rate)
            total_scatter_events += 1

        # EVALUATE MOISTURE SATURATION: Has the cooling curve hit dew point?
        if T_surf <= T_dew:
            # If wind shear hasn't broken the fog bank apart, engage the thermal cap
            if lwp_active > 5.0:
                T_surf = T_dew
                T_surf_k = T_dew + 273.15
                fog_hours_accumulated += dt / 3600.0

            # Condense liquid water path directly at ground level
            condensation_rate = 0.15
            lwp_active += condensation_rate

            # Latent heat flux calculation
            latent_heat_flux = (condensation_rate / 1000.0) * L_v / dt
        else:
            latent_heat_flux = 0.0

        # 6. Compute Dynamic Downwelling Infrared Flux
        R_clear_down = epsilon_a * sigma * (T_atm_k**4)
        cloud_emissivity_factor = 1.0 - np.exp(-k_lw * lwp_active)
        R_cloud_down = cloud_emissivity_factor * sigma * (T_surf_k**4) * 0.22
        total_longwave_down = R_clear_down + R_cloud_down

        # 7. Compute Outwelling Upwelling Flux
        upwelling_longwave_out = epsilon_s * sigma * (T_surf_k**4)

        # 8. Net Energy Balance Matrix
        Q_net = total_longwave_down - upwelling_longwave_out + latent_heat_flux

        # Only execute temperature drop if we are not thermally locked by fog blanket
        if T_surf > T_dew or lwp_active <= 5.0:
            dT_dt = Q_net / C_s
            T_surf += dT_dt * dt

    total_drop_c = initial_temp_c - T_surf
    return T_surf, total_drop_c, lwp_active, fog_hours_accumulated, total_scatter_events


if __name__ == "__main__":
    print("=================================================================")
    print("      NWS SENSOR COUPLED WIND SHEAR & FOG SCATTER ENGINE        ")
    print("=================================================================")
    print("Simulating a 12-Hour Night starting at 25.0°C (77.0°F)...")
    print("Evaluating how wind velocity shifts radiative cooling curves:\n")

    # Evaluate changing wind regimes under identical high-humidity conditions
    wind_scenarios = {
        "Calm Night Profile (Dense Stable Fog)": {
            "base_wind": 2.0,
            "gust_scale": 0.02,
        },
        "Breezy Night Profile (Intermittent Scattering)": {
            "base_wind": 6.0,
            "gust_scale": 0.08,
        },
        "Gale Force Profile (Total Shear Clearing)": {
            "base_wind": 14.0,
            "gust_scale": 0.15,
        },
    }

    # Run Simulation Loop
    for label, wind_params in wind_scenarios.items():
        final_t, drop_c, final_lwp, fog_hrs, scatter_count = (
            simulate_cooling_with_wind_shear(
                lwp_initial=0.0,
                initial_temp_c=25.0,
                initial_dewpoint_c=16.0,
                base_wind_mph=wind_params["base_wind"],
                gust_frequency=wind_params["gust_scale"],
            )
        )

        print(f"💨 Wind Regime: {label}")
        print(f"   -> Inputs: Base Wind = {wind_params['base_wind']} mph | Gust Scale Factor = {wind_params['gust_scale']}")
        print(f"   -> Mechanical Shear Incidents: {scatter_count} minutes of active fog stripping")
        print(f"   -> Final Morning Temp:         {final_t:.2f}°C")
        print(f"   -> Net Overnight Temp Drop:    {drop_c:.2f}°C")

        if fog_hrs > 0:
            print(f"   -> 🌁 Sustained Fog Duration:  {fog_hrs:.2f} hours locked at dew point")
            print(f"   -> Residual Cloud Mass density: {final_lwp:.1f} g/m² remaining")
        else:
            print("   -> 🌁 Sustained Fog Duration:  0.00 hours (Turbulent mixing scattered fog structure)")
        print("-" * 75)
