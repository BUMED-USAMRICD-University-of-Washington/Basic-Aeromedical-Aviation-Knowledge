import os
import struct
import pandas as pd

def parse_stellarium_catalog(file_path):
    """
    Parses the Stellarium catalog-3.23.dat file.
    Returns a Pandas DataFrame containing the extracted celestial objects.
    """
    print(f"Attempting to read: {file_path}...")
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Could not find the catalog file at {file_path}")

    # Method 1: Attempt to read as Tab-Separated Text (TSV) or CSV
    # Stellarium's modern DSO catalogs often use a tab-separated format with '#' for comments.
    try:
        # Read the first few bytes to check if it's obviously binary
        with open(file_path, 'rb') as f:
            header_check = f.read(4)
            
        # If it doesn't look like a binary magic number, process as text
        if b'\x00' not in header_check:
            print("Detected text-based catalog format. Parsing as TSV...")
            
            # Common columns in Stellarium DSO files: 
            # ID, RA, Dec, Type, Morphological Type, Magnitude, Size/Diameter, Distance, Name
            df = pd.read_csv(
                file_path, 
                sep='\t',          # Tab separated
                comment='#',       # Ignore header comments
                low_memory=False,
                names=["ID", "RA", "Dec", "Type", "Morph_Type", "Mag", "Size_Arcmin", "Orientation", "Name"]
            )
            
            # Clean up the data
            df = df.dropna(subset=['RA', 'Dec'])
            print(f"Successfully loaded {len(df)} objects.")
            return df
            
    except Exception as e:
        print(f"Text parsing failed: {e}. Moving to binary fallback.")

    # Method 2: Binary Struct Parsing (Fallback)
    # If the .dat file is a compiled binary catalog, it uses fixed-byte records.
    print("Detected binary catalog format. Unpacking C-structs...")
    objects = []
    
    with open(file_path, 'rb') as f:
        # Stellarium binary files usually have a file header (e.g., 32 bytes)
        # Magic number, catalog ID, record count, etc.
        header_data = f.read(32) 
        
        # We process the file record by record. 
        # (Assuming a standard 24-byte record size for example purposes - adjust if documentation dictates otherwise)
        record_size = 24 
        
        while True:
            record = f.read(record_size)
            if not record or len(record) < record_size:
                break
                
            # Unpack the binary record. 
            # Example struct: i (int, 4 bytes), f (float, 4 bytes)
            # Format: ID(int), RA(float), Dec(float), Mag(float), Size(float), Type(int)
            try:
                unpacked_data = struct.unpack('<iffffi', record)
                
                obj_dict = {
                    "ID": unpacked_data[0],
                    "RA": unpacked_data[1],        # Right Ascension
                    "Dec": unpacked_data[2],       # Declination
                    "Mag": unpacked_data[3],       # Visual Magnitude
                    "Size_Arcmin": unpacked_data[4], # Angular size
                    "Type": unpacked_data[5]       # Object type code
                }
                objects.append(obj_dict)
            except struct.error:
                break

    df = pd.DataFrame(objects)
    print(f"Successfully unpacked {len(df)} binary records.")
    return df

# ==========================================
# Execution Block
# ==========================================
if __name__ == "__main__":
    # Point this to where you downloaded catalog-3.23.dat
    catalog_path = "catalog-3.23.dat" 
    
    try:
        # 1. Parse the catalog
        astro_data = parse_stellarium_catalog(catalog_path)
        
        # 2. Preview the first 5 rows to verify coordinates and magnitudes
        print("\n--- Data Preview ---")
        print(astro_data.head())
        
        # 3. Filter out objects without magnitude or size data 
        # (We need these for our Mass/Size equation engine)
        processable_targets = astro_data[
            (astro_data['Mag'].notnull()) & 
            (astro_data['Size_Arcmin'].notnull())
        ]
        
        print(f"\nReady for Engine: {len(processable_targets)} objects have enough data to calculate mass/size.")
        
    except FileNotFoundError as e:
        print(e)
        print("Please ensure 'catalog-3.23.dat' is in the same directory as this script.")
