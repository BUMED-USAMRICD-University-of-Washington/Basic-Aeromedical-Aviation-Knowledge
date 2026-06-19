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

import struct

def encode_to_1553b_avionics_bus(jit_output_array):
    """
    Serializes continuous JIT guidance outputs into signed 16-bit 
    MIL-STD-1553B data words using custom fixed-point binary scales.
    Maximum message envelope is 32 words long.
    """
    vs_fpm        = jit_output_array[0] # Word 1: Vertical Speed
    hdg_deg       = jit_output_array[1] # Word 2: Commanded Heading
    xwind_kts     = jit_output_array[2] # Word 3: Crosswind Component
    fuel_flow     = jit_output_array[3] # Word 4: Fuel Flow rate
    bingo_lbs     = jit_output_array[4] # Word 5: Bingo limit
    endurance_min = jit_output_array[5] # Word 6: Holding endurance mins

    # Convert floats to fixed-point integers to fit the 16-bit bus architecture
    word_vs     = int(clamp(vs_fpm, -32768, 32767))
    word_hdg    = int((hdg_deg / 360.0) * 32767)       # Scaled binary fraction
    word_xwind  = int(clamp(xwind_kts * 100, -32768, 32767)) # 0.01 knot resolution
    word_flow   = int(clamp(fuel_flow, 0, 32767))
    word_bingo  = int(clamp(bingo_lbs / 10, 0, 32767))  # 10-lb resolution blocks
    word_endure = int(clamp(endurance_min * 10, 0, 32767)) # 0.1 minute resolution
    
    # Pack into Big-Endian network format string (hhhhhh = 6 signed short words)
    binary_1553b_payload = struct.pack(">hhhhhh", word_vs, word_hdg, word_xwind, word_flow, word_bingo, word_endure)
    return binary_1553b_payload

def clamp(val, min_val, max_val):
    return max(min_val, min(val, max_val))

def export_to_nasa_hdf5(file_path, simulation_id, telemetry_data, np_waypoints):
    """Appends array waypoints and run characteristics to a NASA HDF5 repository file."""
    with h5py.File(file_path, "a") as f:
        grp = f.create_group(f"sim_run_{simulation_id}")
        grp.create_dataset("waypoints", data=np_waypoints, compression="gzip")
        grp.attrs["airport"] = telemetry_data["airport"]
        grp.attrs["selected_side"] = telemetry_data["selected_runway_side"]
        grp.attrs["pattern_entry"] = telemetry_data["resolved_pattern_type"]
        grp.attrs["crosswind_kts"] = telemetry_data["calculated_crosswind_knots"]
