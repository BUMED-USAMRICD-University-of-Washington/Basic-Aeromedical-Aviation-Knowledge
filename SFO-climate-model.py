import numpy as np
import matplotlib.pyplot as plt

def simulate_sf_climate():
    print("--- San Francisco Climate Superposition Model ---")
    start_year = int(input("Enter starting year (e.g., 1850): "))
    end_year = int(input("Enter ending year (e.g., 2026): "))
    
    # Time vector (yearly steps)
    t = np.arange(start_year, end_year + 1)
    
    # Coefficients optimized for SF's coastal microclimate
    T_0 = 14.0            # Baseline average temp in Celsius
    alpha_SF = 0.008      # Dampened human warming trend (C/year) due to ocean buffer
    
    # Cyclical Ocean/Solar Amplitudes (A) and Periods (P) in years
    # A_PDO, P_PDO
    A_1, P_1, phi_1 = 0.65, 55.0, 0.2
    # A_ENSO, P_ENSO
    A_2, P_2, phi_2 = 0.45, 4.5, 0.7
    # A_Solar, P_Solar
    A_3, P_3, phi_3 = 0.15, 11.0, 0.0
    
    # Underlying trend
    base_trend = T_0 + alpha_SF * (t - start_year)
    
    # Summing the cycles (Fourier Series components)
    pdo_cycle = A_1 * np.sin((2 * np.pi / P_1) * t + phi_1)
    enso_cycle = A_2 * np.sin((2 * np.pi / P_2) * t + phi_2)
    solar_cycle = A_3 * np.sin((2 * np.pi / P_3) * t + phi_3)
    
    # Unpredictable microclimate noise
    np.random.seed(42)
    epsilon = np.random.normal(0, 0.25, len(t))
    
    # Final Superposition Equation
    T_SF = base_trend + pdo_cycle + enso_cycle + solar_cycle + epsilon
    
    # Plotting the results
    plt.figure(figsize=(12, 6))
    plt.plot(t, T_SF, label='Modeled SF Temp Anomaly', color='teal', alpha=0.8)
    plt.plot(t, base_trend, label='Anthropogenic Base Trend', color='crimson', linestyle='--', linewidth=2)
    plt.title(f"Multi-Century Harmonic Temperature Profile for San Francisco ({start_year}-{end_year})")
    plt.xlabel("Year")
    plt.ylabel("Temperature (°C)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    print("[Success] Climate simulation matrix generated.")

if __name__ == "__main__":
    simulate_sf_climate()
