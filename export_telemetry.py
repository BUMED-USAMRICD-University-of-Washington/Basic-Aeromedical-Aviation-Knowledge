import os
import json
import time
import numpy as np
import fcntl
import struct
import zlib
import h5py

from nasa_telemetry_exporter import NASATelemetryExporter
from lockheed_telemetry_exporter import LockheedTelemetryExporter
from axiom_telemetry_exporter import AxiomTelemetryExporter
from northrop_grumman_exporter import NorthropGrummanExporter
from oaam_exporter import OAAMTelemetryExporter
from boeing_telemetry_bridge import BoeingTelemetryBridge 

class TelemetryDispatcher:
    def __init__(self, output_dir="logs"):
        self.output_dir = output_dir
        
        """Guard 1: Ensure directory exists without nested if/else traps"""
        if not os.path.exists(self.output_dir): 
            os.makedirs(self.output_dir)

        """RESTORED: Corrected indentation. Instantiating institutional exporters safely."""
        self.nasa = NASATelemetryExporter()
        self.lockheed = LockheedTelemetryExporter()
        self.axiom = AxiomTelemetryExporter()
        self.northrop = NorthropGrummanExporter()
        self.oaam = OAAMTelemetryExporter()
        self.boeing = BoeingTelemetryBridge()

    def _write_safe(self, filename, data_bytes):
        """Atomic write ensures data integrity for mission buses."""
        
        """Guard 1: Prevent writing empty frames"""
        if not data_bytes:
            return False
            
        with open(f"{self.output_dir}/{filename}", "ab") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(data_bytes)
            fcntl.flock(f, fcntl.LOCK_UN)
            
        return True

    def _generate_northrop_frame(self, payload):
        """RESTORED: Packs Big-Endian binary struct for military hardware ingestion."""
        
        """Guard 1: Ensure critical spatial data exists"""
        if 'lat' not in payload or 'pitch' not in payload:
            return b''
            
        """Struct Format: > (Big Endian), H (Header), f (6 floats: lat, lon, alt, p, r, y)"""
        frame = struct.pack(
            ">Hffffff", 
            0xABCD, 
            float(payload.get('lat', 0.0)),
            float(payload.get('lon', 0.0)),
            float(payload.get('alt', 0.0)),
            float(payload.get('pitch', 0.0)),
            float(payload.get('roll', 0.0)),
            float(payload.get('yaw', 0.0))
        )
        
        checksum = zlib.crc32(frame) & 0xFFFFFFFF
        return frame + struct.pack(">I", checksum)

    def _write_h5_flight_record(self, payload, timestamp):
        """RESTORED: High-fidelity HDF5 datastore for NASA/Lockheed post-flight analysis."""
        
        h5_file = f"{self.output_dir}/mission_flight_data.h5"
        
        with h5py.File(h5_file, 'a') as hf:
            """Ensure core dataset exists or create it"""
            if 'telemetry_stream' not in hf:
                hf.create_dataset('telemetry_stream', (0, 7), maxshape=(None, 7), dtype='float64')
                
            """Shape: [Timestamp, Lat, Lon, Alt, Pitch, Roll, Yaw]"""
            data_vector = np.array([[
                float(timestamp),
                float(payload.get('lat', 0.0)),
                float(payload.get('lon', 0.0)),
                float(payload.get('alt', 0.0)),
                float(payload.get('pitch', 0.0)),
                float(payload.get('roll', 0.0)),
                float(payload.get('yaw', 0.0))
            ]])
            
            """Dynamically resize HDF5 dataset and append"""
            dataset = hf['telemetry_stream']
            dataset.resize((dataset.shape[0] + 1, 7))
            dataset[-1:] = data_vector

    def dispatch(self, payload):
        """The Master Routing Logic."""
        
        """Guard 1: Do not dispatch empty matrices"""
        if not payload:
            return
            
        current_time = int(time.time())
            
        """1. Write human-readable JSON state"""
        with open(f"{self.output_dir}/telemetry_{current_time}.json", "w") as f:
            json.dump(payload, f, indent=4)
            
        """2. Write high-fidelity HDF5 physics record"""
        self._write_h5_flight_record(payload, current_time)
            
        """3. Trigger individual institutional hooks"""
        self.nasa.dispatch(payload, self.output_dir)
        self.lockheed.dispatch(payload, self.output_dir)
        self.axiom.dispatch(payload, self.output_dir)
        self.northrop.dispatch(payload, self.output_dir)
        self.oaam.dispatch(payload, self.output_dir)
        self.boeing.dispatch(payload, self.output_dir)
        
        print("Global Telemetry Dispatched: [Boeing] [NASA] [Lockheed] [Axiom] [Northrop] [OAAM]")


if __name__ == "__main__":
    dispatcher = TelemetryDispatcher()
    test_payload = {
        "temp_c": 15.5, "pressure_hpa": 1013.2, 
        "lat": 47.4480, "lon": -122.3088, "alt": 3000.0,
        "pitch": 5.0, "roll": 0.0, "yaw": 180.0
    }
    dispatcher.dispatch(test_payload)
