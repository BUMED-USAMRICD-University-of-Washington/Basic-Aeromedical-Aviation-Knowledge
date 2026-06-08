# --- PRIMARY ENGINE: Radiation Modeling & Thermodynamics ---
import math
import pandas as pd
from numba import njit

# --- SECONDARY ENGINE DEPENDENCIES ---
import telemetry_link          # NEW: Integrated Centralized Data Bus
import aviation_physics        # Core math
import aviation_telemetry      # Data flow

try:
    import cupy as np  # Attempt to use GPU-accelerated array math
    print("🚀 NVIDIA GPU Acceleration Engaged (Radiation Matrix)")
except ImportError:
    import numpy as np # Fallback to standard CPU math
    print("⚡ Using CPU (NVIDIA acceleration not detected)")


# =========================================================================
# GLOBAL THERMODYNAMIC CONSTANTS
# =========================================================================
STEFAN_BOLTZMANN = 5.670374419e-8  # W / (m^2 * K^4)
LUMINOSITY_SUN_W = 3.828e26        # Watts
RADIUS_SUN_M     = 6.957e8         # Meters
LUMINOUS_EFFICACY_SUN = 93.0       # Approximate Lumens per Watt for a G-type star


# =========================================================================
# 1. EARTH ATMOSPHERIC RADIATION BALANCE
# =========================================================================
@njit(fastmath=True)
def calculate_radiative_flux(cloud_fraction, surface_albedo, temp_surface_k, temp_cloud_base_k, solar_zenith_deg):
    """
    Computes the Shortwave (Solar) and Longwave (Infrared) energy balance.
    Compiled via Numba for high-performance floating point operations.
    """
    solar_constant = 1361.0 # W/m^2 at top of atmosphere
    
    # 2. Shortwave (Solar) Flux Calculation
    zenith_rad = solar_zenith_deg * (math.pi / 180.0)
    cos_zenith = max(0.0, math.cos(zenith_rad))
    
    # Dynamic Albedo factoring in cloud cover
    cloud_albedo_factor = 0.55 * cloud_fraction
    total_effective_albedo = surface_albedo + cloud_albedo_factor - (surface_albedo * cloud_albedo_factor)
    
    sw_down_surface = solar_constant * cos_zenith * (1.0 - cloud_albedo_factor)
    sw_net = sw_down_surface * (1.0 - total_effective_albedo)

    # 3. Longwave (Infrared) Flux Calculation
    # Upwelling from the surface
    lw_up = STEFAN_BOLTZMANN * (temp_surface_k ** 4)
    
    # Downwelling from the atmosphere/clouds
    effective_emissivity = 0.76 + (0.95 - 0.76) * cloud_fraction
    lw_down = effective_emissivity * STEFAN_BOLTZMANN * (temp_cloud_base_k ** 4)
    
    lw_net = lw_down - lw_up

    # 4. Total Net Radiative Flux Balance
    net_flux = sw_net + lw_net
    
    return sw_net, lw_net, net_flux


def run_radiation_layer(telemetry_override=None):
    """
    Main orchestration function for local cloud/surface balance.
    """
    print("☀️ Running Cloud Radiative Flux Balance Layer...")
    
    c_frac = 0.5            
    s_albedo = 0.2          
    t_surf_c = 15.0         
    t_cloud_c = 5.0         
    zenith = 45.0           
    
    if telemetry_override:
        c_frac = telemetry_override.get('cloud_fraction', c_frac)
        s_albedo = telemetry_override.get('surface_albedo', s_albedo)
        t_surf_c = telemetry_override.get('temp_c', t_surf_c)
        t_cloud_c = telemetry_override.get('cloud_base_temp_c', t_cloud_c)
        zenith = telemetry_override.get('solar_zenith_deg', zenith)

    t_surf_k = t_surf_c + 273.15
    t_cloud_k = t_cloud_c + 273.15

    sw_net, lw_net, total_net = calculate_radiative_flux(
        cloud_fraction=c_frac,
        surface_albedo=s_albedo,
        temp_surface_k=t_surf_k,
        temp_cloud_base_k=t_cloud_k,
        solar_zenith_deg=zenith
    )
    
    payload = {
        "shortwave_net_flux_w_m2": round(sw_net, 15),
        "longwave_net_flux_w_m2": round(lw_net, 15),
        "total_net_flux_w_m2": round(total_net, 15),
        "cooling_regime_active": bool(total_net < 0.0), 
        "solar_zenith_deg": zenith,
        "cloud_fraction": c_frac
    }
    
    telemetry_link.update_global_state("atmospheric_models", "radiation_flux", payload)
    return payload


# =========================================================================
# 2. DEEP SPACE STELLAR THERMODYNAMICS 
# =========================================================================
@njit(fastmath=True)
def compute_stellar_thermodynamics_vectorized(masses_solar, radii_solar):
    """
    Calculates the surface temperature (Heat) and
