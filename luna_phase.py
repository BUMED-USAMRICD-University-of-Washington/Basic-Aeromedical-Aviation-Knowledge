def run_lunar_phase_modulation():
    print("\n--- Lunar Synodic Phase Anomaly Map ---")
    target_month_start = float(input("Enter start index day of lunar calendar (0 = New Moon): "))
    
    # Arrays mapping out a full 29.53 day synodic month
    t = np.linspace(target_month_start, target_month_start + 29.53, 500)
    P_syn = 29.53
    
    # Set localized coefficients derived from historical data filtering
    A_grav = 0.08      # Gravitational pressure anomaly impact limit
    phi_grav = 3.5     # 3-5 day moisture latency delay for rain drops
    A_therm = 0.03     # Stratospheric thermal albedo factor
    phi_therm = 1.0    # 1 day thermal atmospheric lag
    
    # The Matrix Components
    # Twice a month cycle (New and Full alignment peaks)
    gravity_wave = A_grav * np.cos((4 * np.pi / P_syn) * t - phi_grav)
    # Once a month cycle (Full moon peak brightness)
    thermal_wave = A_therm * np.cos((2 * np.pi / P_syn) * t - phi_therm)
    
    # Total Composite Synodic Signal
    Y_phase = gravity_wave + thermal_wave
    
    # Plotting Phase Trends
    plt.figure(figsize=(12, 6))
    plt.plot(t, Y_phase, label='Total Lunar Signal Anomaly', color='purple', linewidth=2.5)
    plt.plot(t, gravity_wave, label='Gravitational Component (2x/month)', color='blue', linestyle=':', alpha=0.6)
    plt.plot(t, thermal_wave, label='Thermal Albedo Component (1x/month)', color='orange', linestyle='--', alpha=0.6)
    plt.axvline(14.77, color='gold', linestyle='-', alpha=0.5, label='Full Moon Centerline')
    plt.title("Synodic Lunar Phase Modulation Waveform")
    plt.xlabel("Days Since New Moon")
    plt.ylabel("Normalized Atmospheric Variance Value")
    plt.legend()
    plt.grid(True, alpha=0.2)
    print("[Success] Synodic wave processing loops complete.")

if __name__ == "__main__":
    run_lunar_phase_modulation()
    plt.show()
