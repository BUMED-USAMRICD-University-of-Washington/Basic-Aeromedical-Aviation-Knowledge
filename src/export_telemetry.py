import struct
import h5py
import numpy as np

def export_to_1553b_binary(waypoint_stack):
    """
    Encodes waypoints into MIL-STD-1553B compliant 16-bit signed integer words.
    Scale factor typical for flight management computers.
    """
    binary_payload = b""
    # 1553B messages are limited to 32 data words (64 bytes)
    for wp in waypoint_stack[:16]:  # Max 16 coordinates (Lat/Lon pairs)
        # Convert floats to fixed-point scaled binary values
        lat_scaled = int(wp["lat"] * 10000)
        lon_scaled = int(wp["lon"] * 10000)
        
        # Pack into signed short binary blocks ('h' is 16-bit signed int)
        binary_payload += struct.pack(">hh", lat_scaled, lon_scaled)
        
    return binary_payload

def export_to_nasa_hdf5(file_path, simulation_id, telemetry_data, np_waypoints):
    """Appends array waypoints and run characteristics to a NASA HDF5 repository file."""
    with h5py.File(file_path, "a") as f:
        grp = f.create_group(f"sim_run_{simulation_id}")
        grp.create_dataset("waypoints", data=np_waypoints, compression="gzip")
        grp.attrs["airport"] = telemetry_data["airport"]
        grp.attrs["selected_side"] = telemetry_data["selected_runway_side"]
        grp.attrs["pattern_entry"] = telemetry_data["resolved_pattern_type"]
        grp.attrs["crosswind_kts"] = telemetry_data["calculated_crosswind_knots"]
