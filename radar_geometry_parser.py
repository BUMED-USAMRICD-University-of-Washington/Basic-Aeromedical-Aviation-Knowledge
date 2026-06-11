import numba
from dynamic_memory_cache import DynamicMemoryCache
shared_cache = DynamicMemoryCache(percentage=0.5)
try:
    import cupy as xp
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Array Batching Active (Performance)")
except ImportError:
    import numpy as xp
    HAS_GPU = False
import io
from numba import njit
import pandas as pd
import matplotlib.pyplot as plt
import aircraft_perf
import aviation_telemetry
import sensor_thermodynamics
import aerodynamic_matrix
import aviation_physics
@njit(fastmath=True)
def load_volumetric_radar_data(telemetry_override=None, raw_text_data):
    """
    Parses the raw attribute table containing radar beam heights and trackpoints.
    This creates a 3D profile of the radar coverage for each ICAO station.
    """
    df = pd.read_csv(io.StringIO(raw_text_data), sep='\s{2,}', engine='python')
    df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
    radar_profiles = {}
    for icao, group in df.groupby('icao'):
        # Sort by height to build the beam from the ground up
        group = group.sort_values(by='height')
        radar_profiles[icao] = {
            "total_trackpoints": int(group['number_of_trackpoints'].sum()),
            "beam_type": group['beam'].iloc[0],
            "lowest_scan_height_ft": int(group['height'].min()),
            "highest_scan_height_ft": int(group['height'].max()),
            "volumetric_slices": group[['height', 'number_of_trackpoints']].to_dict(orient='records')
        }
    return radar_profiles
@njit(fastmath=True)
def check_sensor_coverage(radar_profile, target_sensor_elevation_ft):
    """
    Determines if the radar's lowest beam overshoots the physical NWS thermometer.
    """
    lowest_beam = radar_profile['lowest_scan_height_ft']
    if lowest_beam > target_sensor_elevation_ft:
        return {
            "status": "OVERSHOOT",
            "blind_spot_gap_ft": lowest_beam - target_sensor_elevation_ft,
            "warning": "Radar misses surface microclimate (UHI/Fog)."
        }
    return {"status": "COVERED", "blind_spot_gap_ft": 0}
