import math
import matplotlib.pyplot as plt
import numba
from dynamic_memory_cache import DynamicMemoryCache
shared_cache = DynamicMemoryCache(percentage=0.04)
from numba import njit
import aviation_telemetry
import aviation_physics
import telemetry_link
try:
    import cupy as xp
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Array Batching Active (Performance)")
except ImportError:
    import numpy as xp
    HAS_GPU = False
    print("CPU Fallback: Standard Vectorization Active (Performance)")
STEFAN_BOLTZMANN = 5.670374419e-8  # W / (m^2 * K^4)
LUMINOSITY_SUN_W = 3.828e26        # Watts
RADIUS_SUN_M     = 6.957e8         # Meters
LUMINOUS_EFFICACY_SUN = 93.0       # Approximate Lumens per Watt for a G-type star

@njit(fastmath=True)
def compute_atmospheric_attenuation(flux_toa_wm2, altitude_m):
    """Beer-Lambert Law: Calculates radiation surviving atmospheric absorption."""
    
    """Guard 1: Above the Karman line (100km), no atmosphere to block radiation"""
    if altitude_m >= 100000.0:
        return flux_toa_wm2 
        
    """Guard 2: Prevent negative altitude physics errors"""
    if altitude_m <= 0.0:
        altitude_m = 0.0 
        
    """Calculate atmospheric depth (Scale height approximation ~8500m)"""
    depth = math.exp(-altitude_m / 8500.0)
    mu_attenuation = 0.005 
    
    return flux_toa_wm2 * math.exp(-mu_attenuation * depth)

@njit(fastmath=True)
def compute_radiation_interference(xray_flux_wm2, altitude_m):
    """Calculates radar/ADS-B signal degradation percentage caused by solar scattering."""
    
    """Guard 1: Tropospheric shielding fully protects sensors below 30,000 ft (9144 m)"""
    if altitude_m < 9144.0:
        return 0.0
        
    """Guard 2: X-Class solar flares cause maximum radar blindness (100 percent penalty)"""
    if xray_flux_wm2 >= 1e-4:
        return 1.0
        
    baseline_flux = 1e-8
    
    """Guard 3: Prevent log math errors on negative or perfectly calm sensors"""
    if xray_flux_wm2 <= baseline_flux:
        return 0.0
        
    """Happy Path: Logarithmic scaling for M and C class flares"""
    ratio = xray_flux_wm2 / baseline_flux
    interference = math.log10(ratio) / 4.0
    
    return interference

@njit(fastmath=True)
def compute_hull_radiative_cooling(temp_hull_k, emissivity, surface_area_m2):
    """Stefan-Boltzmann Law: Calculates Watts of heat dumped into space via radiation."""
    
    """Guard: Invalid physical states return zero cooling"""
    if temp_hull_k <= 0.0 or surface_area_m2 <= 0.0 or emissivity <= 0.0:
        return 0.0
        
    STEFAN_BOLTZMANN = 5.670374419e-8
    
    """Space temperature is ~2.7 Kelvin. Subtracting it is mathematically negligible"""
    """compared to a hot hull, so we execute pure raw emission."""
    return emissivity * STEFAN_BOLTZMANN * surface_area_m2 * (temp_hull_k ** 4)

"""THE COLLISION RADAR BRIDGE"""

@njit(fastmath=True)
def get_flux_interference(telemetry_payload=None):
    """The master bridge method called dynamically by collision_avoidance_app.py"""
    
    """Guard: Missing data defaults to a perfectly clear sensor state"""
    if not telemetry_payload:
        return 0.0 
        
    alt_m = telemetry_payload.get('altitude_m', 0.0)
    xray_raw = telemetry_payload.get('xray_flux_wm2', 1e-8)
    
    """Step 1: Filter the space radiation through the atmosphere"""
    surviving_flux = compute_atmospheric_attenuation(xray_raw, alt_m)
    
    """Step 2: Calculate how much the surviving radiation degrades the radar"""
    return float(compute_radiation_interference(surviving_flux, alt_m))

@njit(fastmath=True)
def calculate_radiative_flux_grid(
    cloud_fraction_array, surface_albedo_array, 
    temp_surf_c_array, temp_cloud_c_array, zenith_deg_array
):
    """
    Computes the Shortwave (Solar) and Longwave (Infrared) energy balance
    across an entire geographic grid simultaneously.
    """
    c_frac = xp.array(cloud_fraction_array, dtype=xp.float64)
    s_albedo = xp.array(surface_albedo_array, dtype=xp.float64)
    t_surf_k = xp.array(temp_surf_c_array, dtype=xp.float64) + 273.15
    t_cloud_k = xp.array(temp_cloud_c_array, dtype=xp.float64) + 273.15
    zenith_deg = xp.array(zenith_deg_array, dtype=xp.float64)
    zenith_rad = zenith_deg * (xp.pi / 180.0)
    cos_zenith = xp.maximum(0.0, xp.cos(zenith_rad))
    cloud_albedo_factor = 0.55 * c_frac
    total_effective_albedo = s_albedo + cloud_albedo_factor - (s_albedo * cloud_albedo_factor)
    sw_down_surface = SOLAR_CONSTANT * cos_zenith * (1.0 - cloud_albedo_factor)
    sw_net = sw_down_surface * (1.0 - total_effective_albedo)
    lw_up = STEFAN_BOLTZMANN * (t_surf_k ** 4)
    effective_emissivity = 0.76 + (0.95 - 0.76) * c_frac
    lw_down = effective_emissivity * STEFAN_BOLTZMANN * (t_cloud_k ** 4)
    lw_net = lw_down - lw_up
    net_flux = sw_net + lw_net
    if HAS_GPU:
        return {
            "shortwave_net_w_m2": xp.round(sw_net, 15).get().tolist(),
            "longwave_net_w_m2": xp.round(lw_net, 15).get().tolist(),
            "total_net_w_m2": xp.round(net_flux, 15).get().tolist()
        }
    else:
        return {
            "shortwave_net_w_m2": xp.round(sw_net, 15).tolist(),
            "longwave_net_w_m2": xp.round(lw_net, 15).tolist(),
            "total_net_w_m2": xp.round(net_flux, 15).tolist()
        }

@njit(fastmath=True)
def compute_atmospheric_attenuation(flux_toa_wm2, altitude_m):
    """
    Beer-Lambert Law: Calculates radiation surviving atmospheric absorption.
    """
    # Guard 1: Above the Karman line (100km), no atmosphere to block radiation
    if altitude_m >= 100000.0:
        return flux_toa_wm2 
        
    # Guard 2: Prevent negative altitude physics errors
    if altitude_m <= 0.0:
        altitude_m = 0.0 
        
    # Calculate atmospheric depth (Scale height approximation ~8500m)
    depth = math.exp(-altitude_m / 8500.0)
    mu_attenuation = 0.005 # X-ray absorption coefficient
    
    return flux_toa_wm2 * math.exp(-mu_attenuation * depth)

@njit(fastmath=True)
def compute_radiation_interference(xray_flux_wm2, altitude_m):
    """
    Calculates radar/ADS-B signal degradation percentage caused by solar scattering.
    """
    if altitude_m < 9144.0:
        return 0.0
        
    if xray_flux_wm2 >= 1e-4:
        return 1.0
        
    baseline_flux = 1e-8
    
    if xray_flux_wm2 <= baseline_flux:
        return 0.0
        
    ratio = xray_flux_wm2 / baseline_flux
    interference = math.log10(ratio) / 4.0
    
    return interference

@njit(fastmath=True)
def compute_hull_radiative_cooling(temp_hull_k, emissivity, surface_area_m2):
    """
    Stefan-Boltzmann Law: Calculates Watts of heat dumped into space via radiation.
    """
    if temp_hull_k <= 0.0 or surface_area_m2 <= 0.0 or emissivity <= 0.0:
        return 0.0
        
    STEFAN_BOLTZMANN = 5.670374419e-8
    
    return emissivity * STEFAN_BOLTZMANN * surface_area_m2 * (temp_hull_k ** 4)

@njit(fastmath=True)
def get_flux_interference(telemetry_payload=None):
    """
    The master bridge method called dynamically by collision_avoidance_app.py
    """
    if not telemetry_payload:
        return 0.0 
        
    alt_m = telemetry_payload.get('altitude_m', 0.0)
    xray_raw = telemetry_payload.get('xray_flux_wm2', 1e-8)
    
    surviving_flux = compute_atmospheric_attenuation(xray_raw, alt_m)
    return float(compute_radiation_interference(surviving_flux, alt_m))

@njit(fastmath=True)
def compute_stellar_thermodynamics_grid(masses_solar, radii_solar):
    """
    Calculates the surface temperature (K) and total thermal output (Watts)
    for an entire catalog of celestial bodies simultaneously based on Main Sequence relations.
    """
    mass_arr = xp.array(masses_solar, dtype=xp.float64)
    radius_arr = xp.array(radii_solar, dtype=xp.float64)
    luminosity_solar_ratio = mass_arr ** 3.5
    luminosity_watts = luminosity_solar_ratio * LUMINOSITY_SUN_W
    radius_meters = radius_arr * RADIUS_SUN_M
    surface_area = 4.0 * xp.pi * (radius_meters ** 2)
    temperature_k = (luminosity_watts / (surface_area * STEFAN_BOLTZMANN)) ** 0.25
    if HAS_GPU:
        return {
            "luminosity_w": xp.round(luminosity_watts, 15).get().tolist(),
            "surface_temp_k": xp.round(temperature_k, 15).get().tolist()
        }
    else:
        return {
            "luminosity_w": xp.round(luminosity_watts, 15).tolist(),
            "surface_temp_k": xp.round(temperature_k, 15).tolist()
        }

@njit(fastmath=True)
def run_radiation_layer(telemetry_override=None):
    """Main orchestration function reporting to Boeing/NASA payloads."""
    print("Running Batched Radiative Flux Balance Layer...")
    c_fracs = [0.5]
    s_albedos = [0.2]
    t_surfs = [15.0]
    t_clouds = [5.0]
    zeniths = [45.0]
    if telemetry_override:
        if isinstance(telemetry_override, dict):
            c_fracs = [telemetry_override.get('cloud_fraction', 0.5)]
            s_albedos = [telemetry_override.get('surface_albedo', 0.2)]
            t_surfs = [telemetry_override.get('temp_c', 15.0)]
            t_clouds = [telemetry_override.get('cloud_base_temp_c', 5.0)]
            zeniths = [telemetry_override.get('solar_zenith_deg', 45.0)]
        elif isinstance(telemetry_override, list):
            c_fracs = [t.get('cloud_fraction', 0.5) for t in telemetry_override]
            s_albedos = [t.get('surface_albedo', 0.2) for t in telemetry_override]
            t_surfs = [t.get('temp_c', 15.0) for t in telemetry_override]
            t_clouds = [t.get('cloud_base_temp_c', 5.0) for t in telemetry_override]
            zeniths = [t.get('solar_zenith_deg', 45.0) for t in telemetry_override]
    results = calculate_radiative_flux_grid(c_fracs, s_albedos, t_surfs, t_clouds, zeniths)
    payload = {
        "shortwave_net_flux_w_m2": results['shortwave_net_w_m2'][0],
        "longwave_net_flux_w_m2": results['longwave_net_w_m2'][0],
        "total_net_flux_w_m2": results['total_net_w_m2'][0],
        "cooling_regime_active": bool(results['total_net_w_m2'][0] < 0.0),
        "solar_zenith_deg": zeniths[0],
        "cloud_fraction": c_fracs[0]
    }
    telemetry_link.update_global_state("atmospheric_models", "radiation_flux", payload)
    return payload
if __name__ == "__main__":
    print("=================================================================")
    print("      AEROSPACE THERMODYNAMICS & RADIATION ENGINE (BATCHED)      ")
    print("=================================================================")
    print("\n[TEST 1] Earth Surface Radiative Balance")
    test_c_fracs = [0.0, 0.5, 1.0]
    test_albedos = [0.1, 0.2, 0.8]
    test_t_surfs = [25.0, 15.0, -10.0]
    test_t_clouds= [10.0, 5.0, -20.0]   
    test_zeniths = [10.0, 45.0, 80.0]
    earth_results = calculate_radiative_flux_grid(
        test_c_fracs, test_albedos, test_t_surfs, test_t_clouds, test_zeniths
    )
    for i in range(3):
        print(f"Sector {i+1}: Net Flux = {round(earth_results['total_net_w_m2'][i], 2)} W/m²")
    print("\n[TEST 2] Deep Space Stellar Surface Calculation")
    test_masses_solar = [1.0, 2.06, 0.12]
    test_radii_solar  = [1.0, 1.71, 0.14]
    stellar_results = compute_stellar_thermodynamics_grid(test_masses_solar, test_radii_solar)
    for i, name in enumerate(["Sol (Earth)", "Sirius A", "Proxima Centauri"]):
        temp = round(stellar_results['surface_temp_k'][i], 2)
        print(f"{name}: Surface Temp = {temp} K")
