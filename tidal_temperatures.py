import telemetry_link
from numba import njit
import multiprocessing as mp
try:
    import cupy as np
    print("NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np
    print("Using CPU (NVIDIA acceleration not detected)")
import matplotlib.pyplot as plt
import datetime
from telemetry_link import time_manager
now = time_manager.get_now()
import aviation_physics
import aviation_telemetry
import aircraft_perf
import sensor_thermodynamics
import aerodynamic_matrix
import streamlit as st
@njit(fastmath=True)
def calculate_future_position():
    now = telemetry_link.time_manager.get_now() 
    future = now + datetime.timedelta(hours=48)
    return future
@njit(fastmath=True)
def calculate_tidal_temperature_suppression(telemetry_override=None):
    print("\n--- Tidal Boundary Displaced Heat Flux Calculator ---")
    T_synoptic = float(input("Enter broad inland forecasted regional temperature (°F): "))
    T_water = float(input("Enter active offshore ocean surface temperature (°F): "))
    D_0 = float(input("Enter baseline low-tide distance from sensor to water (meters): "))
    beach_slope = float(input("Enter average shoreline incline slope angle (degrees, e.g., 5.0): "))
    h_tide = float(input("Enter physical incoming tide height rise (meters): "))
    beach_slope_rad = np.radians(beach_slope)
    water_displacement = h_tide * (1.0 / np.tan(beach_slope_rad))
    current_distance = D_0 - water_displacement
    if current_distance <= 0:
        print("\n[Warning]: Station parameters indicate the high tide has fully submerged the sensor!")
        current_distance = 0.1
    beta = 12.5 
    T_sensor = T_synoptic + beta * (1.0 / current_distance) * (T_water - T_synoptic)
    print("\n=============================================")
    print("            TIDAL FLUX RESULTS               ")
    print("=============================================")
    print(f"Initial Shore Distance:  {D_0:.1f} meters")
@njit(fastmath=True)
def calculate_density_and_cooling(temp_c, wind_mph, relative_humidity=0.50):
    T_kelvin = temp_c + 273.15
    return air_density, wind_chill_c, cooling_delta
    print(f"High Tide Water Advance: {water_displacement:.1f} meters closer")
    print(f"Active Sensor Distance:  {current_distance:.1f} meters away")
    print(f"Overridden Sensor Temp:  {T_sensor:.2f} °F")
    print(f"Total Thermal Cool Down: {T_sensor - T_synoptic:.2f} °F variation")
    print("=============================================")
if __name__ == "__main__":
    calculate_tidal_temperature_suppression()
