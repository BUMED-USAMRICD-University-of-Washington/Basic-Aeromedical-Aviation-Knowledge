import numpy as np


def simulate_runway_performance_log(
    initial_temp=26.0,
    initial_dew=16.0,
    base_wind_mph=8.0,
    gust_scale=0.08,
    runway_heading_deg=90.0,  # e.g., Runway 09 (Heading 090°)
    station_elevation_ft=1026.0,
):
    """Runs a 12-hour runway simulation, logging dynamic Density Altitude,

    along with exact Headwind and Crosswind structural vector arrays.
    """
    # 1. Physical & Thermodynamic Constants
    sigma = 5.670374e-8
    k_lw = 0.022
    epsilon_a = 0.76
    epsilon_s = 0.95
    T_atm_k = 285.15
    C_s = 30000.0
    L_v = 2.501e6
    CRITICAL_GUST_SHEAR = 12.0

    # 2. Aviation Reference System Setup (ISA Standard)
    T_standard_at_elevation = 15.0 - (1.98 * (station_elevation_ft / 1000.0))
    runway_rad = np.radians(runway_heading_deg)

    # Time configuration (720 total iterations)
    dt = 60.0
    total_minutes = 720

    # State initialization
    T_surf = initial_temp
    T_dew = initial_dew
    lwp_active = 0.0
    fog_active_state = False

    np.random.seed(42)

    # Print Formatted Telemetry Table Headers
    print("=" * 145)
    print(
        f"{'MIN':<5} | {'TEMP':<6} | {'WIND':<5} | {'DIR':<4} | "
        f"{'HEADWIND':<9} | {'CROSSWIND':<10} | {'DENSITY ALT':<12} | {'AIRPORT SAFETY MONITORING / ALERTS'}"
    )
    print("=" * 145)

    # 3. Main Step-by-Step Simulation Loop
    for minute in range(1, total_minutes + 1):
        T_surf_k = T_surf + 273.15

        # Stochastic wind speed and directional tracking loops
        current_wind = base_wind_mph + np.random.exponential(
            scale=gust_scale * 100.0
        )
        # Wind direction wanders dynamically around a southwesterly flow (e.g., 220°)
        current_wind_dir = (
            220.0 + np.sin(minute / 10.0) * 15.0 + np.random.normal(0, 5.0)
        ) % 360
        wind_rad = np.radians(current_wind_dir)

        # --- RUNWAY COMPASS MATRIX TRIGONOMETRY ---
        angle_diff_rad = wind_rad - runway_rad
        headwind_mph = current_wind * np.cos(angle_diff_rad)
        crosswind_mph = current_wind * np.sin(angle_diff_rad)

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
        status_message = "🔴 IFR LOCKOUT"

        if current_fog_state != fog_active_state:
            state_triggered_this_minute = True
            fog_active_state = current_fog_state
            status_message = (
                "🌁 FOG FORMED" if current_fog_state else "💨 FOG SCATTERED"
            )
        elif not current_fog_state:
            status_message = "🟢 VFR ACTIVE"

        # --- DYNAMIC DENSITY ALTITUDE MATH ---
        T_surf_f = (T_surf * 9.0 / 5.0) + 32.0
        T_standard_f = (T_standard_at_elevation * 9.0 / 5.0) + 32.0
        density_altitude_ft = station_elevation_ft + (
            120.0 * (T_surf_f - T_standard_f)
        )

        # --- SAFETY THRESHOLD EVALUATION CHECKS ---
        # Flag structural performance hazards
        if abs(crosswind_mph) > 15.0:
            status_message += " ⚠️ CROSSWIND LIMIT EXCEEDED"
        if headwind_mph < 0:
            status_message += " 🚫 TAILWIND HAZARD"
        if density_altitude_ft > (station_elevation_ft + 1500.0):
            status_message += " 📉 PERFORMANCE DROP"

        # Calculate energy matrices
        R_clear_down = epsilon_a * sigma * (T_atm_k**4)
        cloud_emissivity_factor = 1.0 - np.exp(-k_lw * lwp_active)
        R_cloud_down = cloud_emissivity_factor * sigma * (T_surf_k**4) * 0.22
        total_longwave_down = R_clear_down + R_cloud_down
        upwelling_longwave_out = epsilon_s * sigma * (T_surf_k**4)

        Q_net = total_longwave_down - upwelling_longwave_out + latent_heat_flux

        # Step temperature down if not locked by a stable fog blanket
        if T_surf > T_dew or lwp_active <= 5.0:
            dT_dt = Q_net / C_s
            T_surf += dT_dt * dt

        # 4. Dynamic Printing Cadence
        if minute == 1 or minute % 30 == 0 or state_triggered_this_minute:
            marker = ">>> " if state_triggered_this_minute else "    "
            print(
                f"{marker}{minute:<3} | {T_surf:<4.1f}°C | {current_wind:<4.1f}k | {int(current_wind_dir):03}° | "
                f"{headwind_mph:<9.1f} | {crosswind_mph:<10.1f} | {density_altitude_ft:<12.1f} | {status_message}"
            )

    print("=" * 145)
    print(
        f"[Simulation Terminated Complete] Runway Configuration: Heading {int(runway_heading_deg):03}°"
    )


if __name__ == "__main__":
    # Execute runway monitor simulation
    # Testing Runway 09 (Facing Due East) against a Southwest wind profile
    simulate_runway_performance_log(
        initial_temp=28.0,
        initial_dew=15.5,
        base_wind_mph=9.0,
        gust_scale=0.08,
        runway_heading_deg=90.0,  # Runway 09
        station_elevation_ft=1026.0,
    )
