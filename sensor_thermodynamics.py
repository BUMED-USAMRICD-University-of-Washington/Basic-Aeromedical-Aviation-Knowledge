import aviation_physics
import multiprocessing as mp
import numpy as np
try:
    import cupy as xp
    HAS_GPU = True
    print("NVidia CUDA Cores Engaged: Array Batching Active (Performance)")
except ImportError:
    import numpy as xp
    HAS_GPU = False
import numba
from numba import njit
@njit(fastmath=True)
import pandas as pd
import matplotlib.pyplot as plt
import aircraft_perf
import aviation_telemetry
import sensor_thermodynamics
import streamlit as st
import aerodynamic_matrix
try:
    import cupy as np
    print("NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np
    print("Using CPU (NVIDIA acceleration not detected)")
def calculate_wet_sensor_penalty(telemetry_override=None, t_ambient_c, humidity, wind_speed_mps, is_wooden_sensor=False, is_raining=True):
    """
    Adjusts the predicted official maximum temperature downward due to 
    evaporative cooling on the physical thermometer enclosure.
    """
    if not is_raining:
        return 0.0
    L_v = 2260.0
    h_c = 10.45 - wind_speed_mps + 10 * (wind_speed_mps ** 0.5)
    e_rate = (100.0 - humidity) * 0.02 * wind_speed_mps 
    material_modifier = 1.0 if is_wooden_sensor else 0.15
    delta_t_evap_c = (L_v * e_rate / (h_c * 1000)) * material_modifier
    delta_t_evap_f = delta_t_evap_c * (9.0/5.0)
    return round(delta_t_evap_f, 2)
def calculate_magnetic_field_cooling(b_field_tesla=5.3e-5, air_density=1.2, humidity=50.0):
    """
    Calculates the theoretical diamagnetic cooling effect of a local magnetic field 
    on the moist air mass surrounding the thermometer target.
    """
    import math
    mu_0 = 4 * math.pi * 1e-7
    c_p = 1005.0
    chi_m_dry = -0.4e-8
    chi_m_water = -9.0e-6
    chi_m_weighted = chi_m_dry + (chi_m_water * (humidity / 100.0))
    delta_t_mag_kelvin = (chi_m_weighted * (b_field_tesla ** 2)) / (2 * mu_0 * air_density * c_p)
    delta_t_mag_f = delta_t_mag_kelvin * (9.0 / 5.0)
    return delta_t_mag_f
