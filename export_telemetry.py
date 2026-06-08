# --- PRIMARY ENGINE: Telemetry Export & Archival ---
import os
import json
import h5py
import struct
import time
import numpy as np

# Importing standard dependencies
import telemetry_link

class TelemetryDispatcher:
    """
    Simultaneously exports flight state to Boeing-compatible JSON
    and NASA-compliant binary/HDF5 formats.
    """
    
    # NASA CCSDS Binary Packet structure: [Sync(2)][ID(2)][Time(8)][Data(48)]
    PACKET_FORMAT = ">HHd12f" 
    SYNC_WORD = 0xEB90

    def __init__(self, output_dir="logs"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def dispatch(self, payload):
        """
        The master export trigger. Pushes data to all configured endpoints.
        """
        # 1. Boeing-Standard JSON Export
        self._export_json(payload)
        
        # 2. NASA-Standard Binary Packet (Real-time Telemetry)
        self._export_nasa_binary(payload)
        
        # 3. NASA-Standard HDF5 (Instrument/Spatial Grid Data)
        # Assuming payload contains complex arrays or grid metrics
        if 'grid_data' in payload:
            self._export_hdf5(payload['grid_data'])

    def _export_json(self, payload):
        timestamp = int(time.time())
        filename = f"{self.output_dir}/telemetry_{timestamp}.json"
        with open(filename, "w") as f:
            json.dump(payload, f, indent=4)
        print(f"📄 Boeing JSON Logged: {filename}")

    def _export_nasa_binary(self, payload):
        """Serializes telemetry into a compact NASA-style binary stream."""
        # Map telemetry to float list
        data_packet = [
            payload.get('temp_c', 0.0),
            payload.get('pressure_hpa', 0.0),
            payload.get('lat', 0.0),
            payload.get('lon', 0.0),
            payload.get('alt', 0.0),
            *[0.0]*7 # Padding
        ]
        
        packet = struct.pack(
            self.PACKET_FORMAT,
            self.SYNC_WORD,
            0x0001, # Packet ID
            time.time(),
            *data_packet
        )
        
        with open(f"{self.output_dir}/nasa_stream.bin", "ab") as f:
            f.write(packet)
        print(f"📦 NASA Binary Packet Appended")

    def _export_hdf5(self, grid_data):
        """Archives multi-dimensional instrument data (e.g., radar/weather)."""
        filename = f"{self.output_dir}/instrument_archive.h5"
        dataset_name = f"sensor_grid_{int(time.time())}"
        
        with h5py.File(filename, 'a') as f:
            dset = f.create_dataset(dataset_name, data=grid_data, compression="gzip")
            dset.attrs['units'] = 'SI'
            dset.attrs['timestamp'] = time.time()
        print(f"🧬 NASA HDF5 Archive Updated: {dataset_name}")

# ==========================================
# Integration Hook
# ==========================================
def export_telemetry_loop(payload):
    dispatcher = TelemetryDispatcher()
    dispatcher.dispatch(payload)
    return True

if __name__ == "__main__":
    # Test suite to verify the dual-dispatch functionality
    test_payload = {
        "temp_c": 15.5, 
        "pressure_hpa": 1013.2, 
        "lat": 47.4480, 
        "lon": -122.3088, 
        "alt": 3000.0,
        "grid_data": np.random.rand(10, 10)
    }
    
    export_telemetry_loop(test_payload)
