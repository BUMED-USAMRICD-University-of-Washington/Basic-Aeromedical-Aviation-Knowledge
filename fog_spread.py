import numpy as np

def simulate_and_log_fog_lifecycle(telemetry_override=None, initial_temp=25.0, initial_dew=17.0, base_wind=5.0, gust_scale=0.08):
    """
    Runs a 12-hour simulation (720 minutes) and prints a real-time mathematical logging table
    tracking the exact minute fog forms, scatters, or reforms under wind shear.
    """
    # 1. Physics Engine Setup Constants
    sigma = 5.670374e-8  
    k_lw = 0.022         
    epsilon_a = 0.76     
    epsilon_s = 0.95     
    T_atm_k = 285.15     
    C_s = 30000.0        
    L_v = 2.501e6        
    CRITICAL_GUST_SHEAR = 12.0  # Dynamic clearing threshold (mph)

    # Time configuration (720 total iterations)
    dt = 60.0  # 1 minute per step
    total_minutes = 720
    
    # State initialization
    T_surf = initial_temp
    T_dew = initial_dew
    lwp_active = 0.0
    fog_active_state = False  # Track state transitions
    
    np.random.seed(42)  # Enforce structural consistency in gust timelines

    # Print Table Formatted Headers
    print(f"="*95)
    print(f"{'MINUTE':<8} | {'TEMP (°C)':<10} | {'WIND (mph)':<12} | {'LWP (g/m²)':<12} | {'NET FLUX (W/m²)':<16} | {'STATUS / METRIC LOCK':<20}")
    print(f"="*95)

    # 2. Main Step-by-Step Simulation Loop
    for minute in range(1, total_minutes + 1):
        T_surf_k = T_surf + 273.15
        
        # Stochastically calculate wind speed for this exact minute
        current_wind = base_wind + np.random.exponential(scale=gust_scale * 100.0)
        
        # Track if wind shear strips the structural water envelope away
        shear_active = False
        if current_wind >= CRITICAL_GUST_SHEAR and lwp_active > 0:
            lwp_active = max(0.0, lwp_active - 2.5)
            shear_active = True

        # Moisture convergence tracking logic
        latent_heat_flux = 0.0
        if T_surf <= T_dew:
            # If wind shear hasn't broken the liquid water path envelope apart
            if lwp_active > 5.0 and not shear_active:
                T_surf = T_dew
                T_surf_k = T_dew + 273.15
            
            # Condensation loop adds mass to the boundary water layer
            condensation_rate = 0.15
            lwp_active += condensation_rate
            latent_heat_flux = (condensation_rate / 1000.0) * L_v / dt  # Latent heat influx matrix
        
        # State Transition Flag Check (Detect exact minute of state change)
        current_fog_state = (T_surf <= T_dew and lwp_active > 5.0)
        state_triggered_this_minute = False
        status_message = "CLEAR"

        if current_fog_state != fog_active_state:
            state_triggered_this_minute = True
            fog_active_state = current_fog_state
            status_message = "🌁 FOG FORMED" if current_fog_state else "💨 SCATTERED"
        elif current_fog_state:
            status_message = "🌁 FOG LOCKED"

        # Calculate energy matrices
        R_clear_down = epsilon_a * sigma * (T_atm_k**4)
        cloud_emissivity_factor = 1.0 - np.exp(-k_lw * lwp_active)
        R_cloud_down = cloud_emissivity_factor * sigma * (T_surf_k**4) * 0.22
        total_longwave_down = R_clear_down + R_cloud_down
        upwelling_longwave_out = epsilon_s * sigma * (T_surf_k**4)
        
        Q_net = total_longwave_down - upwelling_longwave_out + latent_heat_flux

        # Step temperature progression down if not thermally capped by a stable fog blanket
        if T_surf > T_dew or lwp_active <= 5.0:
            dT_dt = Q_net / C_s
            T_surf += dT_dt * dt

        # 3. Dynamic Printing Logic
        # Log every 30 minutes OR force an entry if a fog state transition happens on this exact minute
        if minute == 1 or minute % 30 == 0 or state_triggered_this_minute:
            # Format forced event markers to visually break out state shifts
            marker = ">>> " if state_triggered_this_minute else "    "
            print(f"{marker}{minute:<4} | {T_surf:<10.2f} | {current_wind:<12.1f} | {lwp_active:<12.2f} | {Q_net:<16.1f} | {status_message:<20}")
            
    print(f"="*95)
    print(f"[Simulation Terminated Complete] Final Morning Temperature: {T_surf:.2f}°C")

if __name__ == "__main__":
    # Initialize simulation with active wind gusts to induce dynamic fog lifecycles
    simulate_and_log_fog_lifecycle(
        initial_temp=22.0, 
        initial_dew=16.5, 
        base_wind=6.5, 
        gust_scale=0.08
    )
