import numpy as np


def simulate_aviation_fog_and_da(
    initial_temp=22.0,
    initial_dew=16.5,
    base_wind=6.5,
    gust_scale=0.08,
    station_elevation_ft=1050.0,
):
    """Runs a 12-hour simulation and prints a step-by-step aviation weather log,

    dynamically calculating real-time Density Altitude variations.
    """
    # 1. Physics Engine Setup Constants
    sigma = 5.670374e-8
    k_lw = 0.022
    epsilon_a = 0.76
    epsilon_s = 0.95
    T_atm_k = 285.15
    C_s = 30000.0
    L_v = 2.501e6
    CRITICAL_GUST_SHEAR = 12.0

    # 2. Aviation Constant Settings (ISA Reference Frame)
    P_standard_sea_level = 29.92  # inHg
    T_standard_sea_level_c = 15.0  # Celsius

    # Calculate Standard Temperature at current airport elevation (1.98°C lapse rate per 1,000 ft)
    T_standard_at_elevation = T_standard_sea_level_c - (
        1.98 * (station_elevation_ft / 1000.0)
    )

    # Time configuration (720 total iterations)
    dt = 60.0
    total_minutes = 720

    # State initialization
    T_surf = initial_temp
    T_dew = initial_dew
    lwp_active = 0.0
    fog_active_state = False

    np.random.seed(42)

    # Print Table Formatted Headers with Aviation Additions
    print("=" * 115)
    print(
        f"{'MINUTE':<7} | {'TEMP (°C)':<9} | {'WIND (mph)':<10} | {'LWP (g/m²)':<11} | {'NET FLUX':<9} | {'DENSITY ALT (ft)':<17} | {'AIRPORT STATUS / ALERTS'}"
    )
    print("=" * 115)

    # 3. Main Step-by-Step Simulation Loop
    for minute in range(1, total_minutes + 1):
        T_surf_k = T_surf + 273.15

        # Stochastic wind speed calculation
        current_wind = base_wind + np.random.exponential(
            scale=gust_scale * 100.0
        )

        # Wind shear scattering check
        shear_active = False
        if current_wind >= CRITICAL_GUST_SHEAR and lwp_active > 0:
            lwp_active = max(0.0, lwp_active - 2.5)
            shear_active = True

        # Moisture convergence tracking logic
        latent_heat_flux = 0.0
        if T_surf <= T_dew:
            if lwp_active > 5.0 and not shear_active:
                T_surf = T_dew
                T_surf_k = T_dew + 273.15

            condensation_rate = 0.15
            lwp_active += condensation_rate
            latent_heat_flux = (condensation_rate / 1000.0) * L_v / dt

        # State Transition Flag Check
        current_fog_state = T_surf <= T_dew and lwp_active > 5.0
        state_triggered_this_minute = False
        status_message = "🔴 IFR: RUNWAY FOG LOCK"

        if current_fog_state != fog_active_state:
            state_triggered_this_minute = True
            fog_active_state = current_fog_state
            status_message = (
                "🌁 FOG FORMED" if current_fog_state else "💨 FOG SCATTERED"
            )
        elif not current_fog_state:
            status_message = "🟢 VFR: CLEAR SKIES"

        # --- DYNAMIC AVIATION DENSITY ALTITUDE MATH ---
        # Convert Celsius temperature to Fahrenheit for National Aviation Standard equations
        T_surf_f = (T_surf * 9.0 / 5.0) + 32.0
        T_standard_f = (T_standard_at_elevation * 9.0 / 5.0) + 32.0

        # Calculate exact Density Altitude using the standard National Weather Service formula:
        # DA = Pressure_Altitude + [120 * (OAT_Fahrenheit - Standard_Temperature_Fahrenheit)]
        # For this boundary engine, baseline Pressure Altitude is mapped directly to airport elevation
        density_altitude_ft = station_elevation_ft + (
            120.0 * (T_surf_f - T_standard_f)
        )

        # Append warning flag to status message if high DA threatens aircraft performance
        if density_altitude_ft > (station_elevation_ft + 1000.0):
            status_message += " ⚠️ HIGH DA FLIGHT ALERT"

        # Calculate energy matrices
        R_clear_down = epsilon_a * sigma * (T_atm_k**4)
        cloud_emissivity_factor = 1.0 - np.exp(-k_lw * lwp_active)
        R_cloud_down = cloud_emissivity_factor * sigma * (T_surf_k**4) * 0.22
        total_longwave_down = R_clear_down + R_cloud_down
        upwelling_longwave_out = epsilon_s * sigma * (T_surf_k**4)

        Q_net = total_longwave_down - upwelling_longwave_out + latent_heat_flux

        # Step temperature progression down if not thermally locked by a stable fog blanket
        if T_surf > T_dew or lwp_active <= 5.0:
            dT_dt = Q_net / C_s
            T_surf += dT_dt * dt

        # 4. Dynamic Printing Cadence
        if minute == 1 or minute % 30 == 0 or state_triggered_this_minute:
            marker = ">>> " if state_triggered_this_minute else "    "
            print(
                f"{marker}{minute:<4} | {T_surf:<9.2f} | {current_wind:<10.1f} | {lwp_active:<11.2f} | {Q_net:<9.1f} | {density_altitude_ft:<17.1f} | {status_message}"
            )

    print("=" * 115)
    print(
        f"[Simulation Terminated] Final Morning Density Altitude: {density_altitude_ft:.1f} feet"
    )


if __name__ == "__main__":
    # Run aviation monitor for Atlanta (KATL) area elevation parameters
    simulate_aviation_fog_and_da(
        initial_temp=27.5,  # Warm afternoon start
        initial_dew=16.0,
        base_wind=5.0,
        gust_scale=0.09,
        station_elevation_ft=1026.0,  # KATL airport field elevation
    )
