# --- PRIMARY ENGINE: Multi-Protocol Telemetry Dispatcher ---
import os
import json
import time
import struct
import h5py
import numpy as np
from numba import njit
import multiprocessing as mp

# =====================================================================
# NASA EXPORTER (HDF5 + CCSDS Binary)
# =====================================================================
class NASATelemetryExporter:
    PACKET_FORMAT = ">HHd12f" # Sync, ID, Time, Data
    SYNC_WORD = 0xEB90

    def dispatch(self, payload, output_dir):
        # 1. Binary Stream
        packet = struct.pack(self.PACKET_FORMAT, self.SYNC_WORD, 0x0001, time.time(), 
                             *[payload.get(k, 0.0) for k in ['temp_c', 'pressure_hpa', 'lat', 'lon', 'alt']]+[0.0]*7)
        with open(f"{output_dir}/nasa_stream.bin", "ab") as f: f.write(packet)
        
        # 2. HDF5 Grid
        if 'grid_data' in payload:
            with h5py.File(f"{output_dir}/instrument_archive.h5", 'a') as f:
                dset = f.create_dataset(f"sensor_grid_{int(time.time())}", data=payload['grid_data'], compression="gzip")
                dset.attrs['timestamp'] = time.time()

# =====================================================================
# LOCKHEED MARTIN EXPORTER (MIL-STD-1553B)
# =====================================================================
class LockheedTelemetryExporter:
    PACKET_FORMAT = ">HHH16H" # Header(3) + 16 Data Words

    @staticmethod
    @njit(fastmath=True)
    def fast_convert_to_fixed_point(data_array):
        output = np.zeros(len(data_array), dtype=np.uint16)
        for i in range(len(data_array)):
            output[i] = int(data_array[i] * 1000.0) & 0xFFFF
        return output

    def dispatch(self, payload, output_dir):
        stream = np.array([payload.get(k, 0.0) for k in ['temp_c', 'pressure_hpa', 'lat', 'lon', 'alt', 'pitch', 'roll', 'yaw']] + [0.0]*8)
        fixed_words = self.fast_convert_to_fixed_point(stream)
        packet = struct.pack(self.PACKET_FORMAT, 0x8000, 0x0001, len(fixed_words), *fixed_words)
        with open(f"{output_dir}/lockheed_bus_dump.bin", "ab") as f: f.write(packet)

# =====================================================================
# MASTER DISPATCHER
# =====================================================================
class TelemetryDispatcher:
    def __init__(self, output_dir="logs"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        self.nasa_exporter = NASATelemetryExporter()
        self.lockheed_exporter = LockheedTelemetryExporter()

    def dispatch(self, payload):
        """Dispatches telemetry simultaneously to all standards."""
        # 1. Boeing JSON
        with open(f"{self.output_dir}/telemetry_{int(time.time())}.json", "w") as f:
            json.dump(payload, f, indent=4)
            
        # 2. NASA
        self.nasa_exporter.dispatch(payload, self.output_dir)
        
        # 3. Lockheed Martin
        self.lockheed_exporter.dispatch(payload, self.output_dir)
        
        print(f"📡 Telemetry dispatched to [JSON/Boeing] [BIN/NASA] [BIN/Lockheed]")

# =====================================================================
# EXECUTION HOOK
# =====================================================================
if __name__ == "__main__":
    dispatcher = TelemetryDispatcher()
    
    # Payload simulating an integrated instrument state
    test_payload = {
        "temp_c": 15.5, "pressure_hpa": 1013.2, 
        "lat": 47.4480, "lon": -122.3088, "alt": 3000.0,
        "pitch": 5.0, "roll": 0.0, "yaw": 180.0,
        "grid_data": np.random.rand(10, 10)
    }
    
    dispatcher.dispatch(test_payload)
