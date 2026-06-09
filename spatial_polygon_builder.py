import numpy as np
from numba import njit
import multiprocessing as mp
@njit(fastmath=True)
import pandas as pd
from dynamic_memory_cache import DynamicMemoryCache
shared_cache = DynamicMemoryCache(percentage=0.50)
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point
import aviation_physics
import multiprocessing as mp
import telemetry_link
import aviation_telemetry
import aircraft_perf
import sensor_thermodynamics
import aerodynamic_matrix
import streamlit as st
try:
    import cupy as xp
    HAS_GPU = True
except ImportError:
    import numpy as xp
    HAS_GPU = False
def build_radar_boundary_arrays(filepath):
    """
    Reads the exported ExpertGPS text file and extracts the vertices.
    Instead of building a CPU-bound Shapely object, it extracts the raw floats
    for the hardware arrays.
    """
    try:
        df = pd.read_csv(filepath, sep='\t')
        coords = df[['Longitude', 'Latitude']].dropna()
        boundary_lons = [round(float(lon), 15) for lon in coords['Longitude']]
        boundary_lats = [round(float(lat), 15) for lat in coords['Latitude']]
        return boundary_lats, boundary_lons
    except Exception as e:
        print(f"Polygon build failure: {e}")
        return [], []
def batched_sensor_coverage_check(boundary_lats, boundary_lons, test_lats, test_lons):
    """
    Hardware-accelerated Point-in-Polygon Ray-Casting Algorithm.
    Checks an entire grid of thousands of sensors against the radar boundary simultaneously.
    """
    poly_y = xp.array(boundary_lats, dtype=xp.float64)
    poly_x = xp.array(boundary_lons, dtype=xp.float64)
    t_y = xp.array(test_lats, dtype=xp.float64)
    t_x = xp.array(test_lons, dtype=xp.float64)
    num_poly_vertices = len(poly_y)
    num_test_points = len(t_y)
    inside_mask = xp.zeros(num_test_points, dtype=xp.bool_)
    j = num_poly_vertices - 1
    for i in range(num_poly_vertices):
        cond1 = (poly_y[i] > t_y) != (poly_y[j] > t_y)
        x_intersect = (poly_x[j] - poly_x[i]) * (t_y - poly_y[i]) / ((poly_y[j] - poly_y[i]) + 1e-15) + poly_x[i]
        cond2 = t_x < x_intersect
        intersecting = cond1 & cond2
        inside_mask = inside_mask ^ intersecting
        j = i
    if HAS_GPU:
        return inside_mask.get().tolist()
    else:
        return inside_mask.tolist()
def run_spatial_layer(boundary_filepath, test_coords):
    """
    Main orchestration function.
    test_coords should be a list of dicts: [{'lat': 40.0, 'lon': -111.0}, ...]
    """
    print("Running Batched Spatial Boundary Checks...")
    poly_lats, poly_lons = build_radar_boundary_arrays(boundary_filepath)
    if not poly_lats:
        return {"status": "ERROR", "reason": "Could not load polygon array"}
    test_lats = [coord.get('lat', 0.0) for coord in test_coords]
    test_lons = [coord.get('lon', 0.0) for coord in test_coords]
    coverage_results = batched_sensor_coverage_check(poly_lats, poly_lons, test_lats, test_lons)
    final_payload = []
    for i in range(len(test_coords)):
        final_payload.append({
            "target_lat": round(float(test_lats[i]), 15),
            "target_lon": round(float(test_lons[i]), 15),
            "is_covered": bool(coverage_results[i])
        })
    telemetry_link.update_global_state("spatial_models", "radar_coverage", final_payload)
    print(f"{len(test_coords)} sensors checked against spatial polygon.")
    return final_payload
if __name__ == "__main__":
    print("=================================================================")
    print("           HIGH-SPEED RADAR POLYGON GRID CHECK (BATCHED)         ")
    print("=================================================================")
    simulated_radar_lats = [40.0, 42.0, 42.0, 40.0]
    simulated_radar_lons = [-112.0, -112.0, -110.0, -110.0]
    test_sensors = [
        {"id": "SENSOR_1", "lat": 41.0, "lon": -111.5},
        {"id": "SENSOR_2", "lat": 39.0, "lon": -111.5},
        {"id": "SENSOR_3", "lat": 41.5, "lon": -113.0},
        {"id": "SENSOR_4", "lat": 41.9, "lon": -110.1},
        {"id": "SENSOR_5", "lat": 45.0, "lon": -100.0}
    ]
    test_lats = [s["lat"] for s in test_sensors]
    test_lons = [s["lon"] for s in test_sensors]
    results = batched_sensor_coverage_check(
        simulated_radar_lats, simulated_radar_lons, test_lats, test_lons
    )
    for idx, sensor in enumerate(test_sensors):
        status = "COVERED" if results[idx] else "BLIND SPOT"
        print(f"{sensor['id']} ({sensor['lat']}, {sensor['lon']}) -> {status}")
