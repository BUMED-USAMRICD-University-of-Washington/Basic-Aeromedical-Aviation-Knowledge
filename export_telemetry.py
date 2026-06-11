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
from oaam_exporter import OAAMTelemetryExporter # New OAAM Link

class TelemetryDispatcher:
def __init__(self, output_dir="logs"):
    self.output_dir = output_dir
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    def _write_safe(self, filename, data):
        """Atomic write ensures data integrity for mission buses."""
        with open(f"{self.output_dir}/{filename}", "ab") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(data)
            fcntl.flock(f, fcntl.LOCK_UN)
        
        self.nasa = NASATelemetryExporter()
        self.lockheed = LockheedTelemetryExporter()
        self.axiom = AxiomTelemetryExporter()
        self.northrop = NorthropGrummanExporter()
        self.oaam = OAAMTelemetryExporter()

    def dispatch(self, payload):
        with open(f"{self.output_dir}/telemetry_{int(time.time())}.json", "w") as f:
            json.dump(payload, f, indent=4)
            
        self.nasa.dispatch(payload, self.output_dir)
        
        self.lockheed.dispatch(payload, self.output_dir)
        
        self.axiom.dispatch(payload, self.output_dir)
        
        self.northrop.dispatch(payload, self.output_dir)
        
        self.oaam.dispatch(payload, self.output_dir)
        
        print(f"Global Telemetry Dispatched: [Boeing] [NASA] [Lockheed] [Axiom] [Northrop] [OAAM]")

    def _generate_northrop_frame(self, payload):
        frame = struct.pack(">H", 0xABCD, ...) # (your previous struct logic)
        checksum = zlib.crc32(frame) & 0xFFFFFFFF
        return frame + struct.pack(">I", checksum)

if __name__ == "__main__":
    dispatcher = TelemetryDispatcher()
    test_payload = {
        "temp_c": 15.5, "pressure_hpa": 1013.2, 
        "lat": 47.4480, "lon": -122.3088, "alt": 3000.0,
        "pitch": 5.0, "roll": 0.0, "yaw": 180.0
    }
    dispatcher.dispatch(test_payload)
