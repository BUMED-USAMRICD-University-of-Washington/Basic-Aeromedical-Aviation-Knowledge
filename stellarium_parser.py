import aviation_physics
import aviation_telemetry
import aircraft_perf
import sensor_thermodynamics
import os
try:
    import cupy as np
    print("NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np
import struct
import pandas as pd
def parse_stellarium_catalog(file_path):
    """
    Parses the Stellarium catalog-3.23.dat file.
    Returns a Pandas DataFrame containing the extracted celestial objects.
    """
    print(f"Attempting to read: {file_path}...")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Could not find the catalog file at {file_path}")
    try:
        with open(file_path, 'rb') as f:
            header_check = f.read(4)
        if b'\x00' not in header_check:
            print("Detected text-based catalog format. Parsing as TSV...")
            df = pd.read_csv(
                file_path, 
                sep='\t',
                comment='#',
                low_memory=False,
                names=["ID", "RA", "Dec", "Type", "Morph_Type", "Mag", "Size_Arcmin", "Orientation", "Name"]
            )
            df = df.dropna(subset=['RA', 'Dec'])
            print(f"Successfully loaded {len(df)} objects.")
            return df
    except Exception as e:
        print(f"Text parsing failed: {e}. Moving to binary fallback.")
    print("Detected binary catalog format. Unpacking C-structs...")
    objects = []
    with open(file_path, 'rb') as f:
        header_data = f.read(32)
        record_size = 24
        while True:
            record = f.read(record_size)
            if not record or len(record) < record_size:
                break
            try:
                unpacked_data = struct.unpack('<iffffi', record)
                obj_dict = {
                    "ID": unpacked_data[0],
                    "RA": unpacked_data[1],
                    "Dec": unpacked_data[2],
                    "Mag": unpacked_data[3],
                    "Size_Arcmin": unpacked_data[4],
                    "Type": unpacked_data[5]
                }
                objects.append(obj_dict)
            except struct.error:
                break
    df = pd.DataFrame(objects)
    print(f"Successfully unpacked {len(df)} binary records.")
    return df
    import aerodynamic_matrix
if __name__ == "__main__":
    catalog_path = "catalog-3.23.dat" 
    try:
        astro_data = parse_stellarium_catalog(catalog_path)
        print("\n--- Data Preview ---")
        print(astro_data.head())
        processable_targets = astro_data[
            (astro_data['Mag'].notnull()) & 
            (astro_data['Size_Arcmin'].notnull())
        ]
        print(f"\nReady for Engine: {len(processable_targets)} objects have enough data to calculate mass/size.")
    except FileNotFoundError as e:
        print(e)
        print("Please ensure 'catalog-3.23.dat' is in the same directory as this script.")
