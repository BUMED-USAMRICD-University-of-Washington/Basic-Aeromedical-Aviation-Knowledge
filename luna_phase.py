import telemetry_link
try:
    import cupy as xp
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Array Batching Active (Performance)")
except ImportError:
    import numpy as xp
    HAS_GPU = False
    print("CPU Fallback: Standard Vectorization Active (Performance)")
import numba
from numba import njit
import multiprocessing as mp
import matplotlib.pyplot as plt
from telemetry_link import time_manager
now = time_manager.get_now()
import aircraft_perf
import aviation_telemetry
import sensor_thermodynamics
import aviation_physics
import aerodynamic_matrix
@njit(fastmath=True)
def calculate_future_position():
    now = telemetry_link.time_manager.get_now() 
    future = now + datetime.timedelta(hours=48)
    return future    
@njit(fastmath=True)
def run_lunar_phase_modulation():
    print("\n--- Lunar Synodic Phase Anomaly Map ---")
    target_month_start = float(input("Enter start index day of lunar calendar (0 = New Moon): "))
    t = np.linspace(target_month_start, target_month_start + 29.53, 500)
    P_syn = 29.53
    A_grav = 0.08
    phi_grav = 3.5
    A_therm = 0.03
    phi_therm = 1.0
    gravity_wave = A_grav * np.cos((4 * np.pi / P_syn) * t - phi_grav)
    thermal_wave = A_therm * np.cos((2 * np.pi / P_syn) * t - phi_therm)
    Y_phase = gravity_wave + thermal_wave
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
