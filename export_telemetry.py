# --- PRIMARY ENGINE: Multi-Protocol Telemetry Dispatcher ---
import os
import json
import time
import numpy as np
import h5py

# Standardized Exporters
from nasa_telemetry_exporter import NASATelemetryExporter
from lockheed_telemetry_exporter import LockheedTelemetryExporter
from axiom_telemetry_exporter import AxiomTelemetryExporter
from northrop_grumman_exporter import NorthropGrummanExporter

class TelemetryDispatcher:
    def __init__(self, output_dir="logs"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        
        # Initialize specialized stream engines
        self.nasa = NASATelemetryExporter()
        self.lockheed = LockheedTelemetryExporter()
        self.axiom = AxiomTelemetryExporter()
        self.northrop = NorthropGrummanExporter()

    def dispatch(self, payload):
        """
        Global Telemetry Dispatch: Forwards state to all contractor/agency protocols.
        """
        # 1. Boeing Standard (Ground UI/JSON)
        with open(f"{self.output_dir}/telemetry_{int(time.time())}.json", "w") as f:
            json.dump(payload, f, indent=4)
            
        # 2. NASA (Science/Deep Space)
        self.nasa.dispatch(payload, self.output_dir)
        
        # 3. Lockheed Martin (Deterministic Avionics)
        self.lockheed.dispatch(payload, self.output_dir)
        
        # 4. Axiom Space (Orbital Data Center)
        self.axiom.dispatch(payload, self.output_dir)
        
        # 5. Northrop Grumman (Open Mission Systems)
        self.northrop.dispatch(payload, self.output_dir)
        
        print(f"🚀 Global Telemetry Dispatched: [Boeing] [NASA] [Lockheed] [Axiom] [Northrop]")

if __name__ == "__main__":
    dispatcher = TelemetryDispatcher()
    test_payload = {
        "temp_c": 15.5, "pressure_hpa": 1013.2, 
        "lat": 47.4480, "lon": -122.3088, "alt": 3000.0,
        "pitch": 5.0, "roll": 0.0, "yaw": 180.0,
        "grid_data": np.random.rand(10, 10)
    }
    dispatcher.dispatch(test_payload)
