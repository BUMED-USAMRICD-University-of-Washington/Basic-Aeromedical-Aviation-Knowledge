# cloud_model.py
# Calculates Cloud Thermodynamic Filtration & Lagrangian Trajectories for NWS Prediction

# --- PRIMARY ENGINE: [Model Name] ---
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- SECONDARY ENGINE DEPENDENCIES ---
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic
import streamlit as st

def calculate_surface_energy_balance(telemetry_override=None, t_rural, lwp, s_downwelling, t_atm, t_base, is_daytime=True):
    """
    Calculates the net surface heat flux and temperature adjustment under cloud filtration.
    Equations:
    Q_net = (1 - alpha) * S_down * T_sw + [epsilon_atm * sigma * T_atm^4 + R_lw_down] - epsilon_surface * sigma * T_surface^4
    """
    # Thermodynamic Constants
    sigma = 5.670374e-8  # Stefan-Boltzmann constant (W/m^2 K^4)
    alpha_surface = 0.15 # Default surface albedo
    epsilon_atm = 0.70   # Atmospheric emissivity
    epsilon_surface = 0.95 # Surface emissivity
    k_sw = 0.05          # Shortwave extinction coefficient
    k_lw = 0.08          # Longwave extinction coefficient
    c_s = 2000.0         # Ground specific heat capacity (J/m^2 K)
    
    # Convert baseline temperatures to Kelvin
    T_rural_K = t_rural + 273.15
    T_atm_K = t_atm + 273.15
    T_base_K = t_base + 273.15
    
    # 1. Daytime Solar Suppression (Shortwave Filtration)
    if is_daytime:
        t_sw = np.exp(-k_sw * lwp)
        shortwave_flux = (1 - alpha_surface) * s_downwelling * t_sw
    else:
        shortwave_flux = 0.0
        
    # 2. Nighttime Thermal Trapping (Longwave Feedback)
    r_lw_down = (1 - np.exp(-k_lw * lwp)) * sigma * (T_base_K ** 4)
    longwave_in = (epsilon_atm * sigma * (T_atm_K ** 4)) + r_lw_down
    
    # 3. Outgoing Surface Longwave Radiation
    longwave_out = epsilon_surface * sigma * (T_rural_K ** 4)
    
    # 4. Net Flux and Temperature Calculation
    q_net = shortwave_flux + longwave_in - longwave_out
    
    # Delta T Calculation (over a one-hour interval = 3600s)
    delta_t = (q_net / c_s) * 3600.0
    
    # Final localized NWS temperature prediction
    t_final = t_rural + (delta_t * (9.0 / 5.0))  # Convert Kelvin delta to Fahrenheit
    
    return {
        "q_net_flux": q_net,
        "delta_t_f": delta_t * (9.0 / 5.0),
        "t_final_predicted": t_final
    }

def calculate_lagrangian_trajectory(pdo_index, amo_index):
    """
    Solves the 2x2 steering matrix for trans-continental cloud paths based on ocean teleconnections.
    M_ocean * Omega = V_steer
    """
    # Empirical Coupling Matrix (gamma values)
    gamma = np.array([[6.5, 1.2], 
                      [-0.5, 4.2]])
    state_vector = np.array([pdo_index, amo_index])
    
    u_zonal, v_meridional = np.dot(gamma, state_vector)
    
    return {
        "U_zonal": u_zonal,          # West-to-East Steering Velocity
        "V_meridional": v_meridional # North-to-South Steering Velocity
    }
