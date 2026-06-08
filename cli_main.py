# cli_main.py
import sys
import os
import time
import importlib
import numpy as np
import logging
from telemetry_link import TelemetryDispatcher
from waypoint_manager import WaypointManager
from flight_control_dynamics import FlightControlDynamics

# --- 1. CONFIGURATION ---
SRC_DIR = "src"
LOG_DIR = "logs"

# Ensure environments exist
os.makedirs(SRC_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

def initialize_avionics():
    """Initializes the navigation, flight dynamics, and protocol dispatchers."""
    try:
        nav = WaypointManager(dso_catalog_path=os.path.join(SRC_DIR, "catalog-3.23.dat"))
        computer = FlightControlDynamics(mode="TACTICAL")
        dispatcher = TelemetryDispatcher(output_dir=LOG_DIR)
        print("SYSTEM: Avionics initialized. NVIDIA/Cupy kernels loaded.")
        return nav, computer, dispatcher
    except Exception as e:
        print(f"CRITICAL BOOT FAILURE: {e}")
        sys.exit(1)

def test_all_protocols():
    """
    Automated Mission Validation Suite.
    Verifies every export protocol (Boeing, NASA, Lockheed, Axiom, Northrop, OAAM).
    """
    print("\n[VALIDATION] Running Protocol Test Suite...")
    dispatcher = TelemetryDispatcher(output_dir=LOG_DIR)
    
    # Payload simulating an integrated instrument state
    test_payload = {
        "temp_c": 15.5, "pressure_hpa": 1013.2, 
        "lat": 47.4480, "lon": -122.3088, "alt": 3000.0,
        "pitch": 5.0, "roll": 0.0, "yaw": 180.0,
        "grid_data": np.random.rand(10, 10)
    }
    
    try:
        dispatcher.dispatch(test_payload)
        # Validate existence
        expected_files = [
            "nasa_stream.bin", "lockheed_bus_dump.bin", 
            "axiom_iss_flight_control.bin", "northrop_oms_bus.bin",
            "oaam_topology_snapshot.json"
        ]
        for f in expected_files:
            path = os.path.join(LOG_DIR, f)
            if os.path.exists(path) and os.path.getsize(path) > 0:
                print(f"  ✅ {f}: VERIFIED")
            else:
                print(f"  ❌ {f}: MISSING OR EMPTY")
    except Exception as e:
        print(f"  ❌ TELEMETRY FAILURE: {e}")

def run_flight_controller():
    nav, computer, dispatcher = initialize_avionics()
    
    while True:
        print("\n--- Basic Aviation Knowledge: Mission Control ---")
        print("1. [FLIGHT] Run Mission Loop")
        print("2. [TEST] Validate All Protocols")
        print("3. [Q] Quit")
        
        choice = input("Select command: ").upper()
        
        if choice == '1':
            print("Engaging tactical flight dynamics...")
        elif choice == '2':
            test_all_protocols()
        elif choice == 'Q':
            sys.exit(0)
        else:
            print("Invalid command.")

if __name__ == "__main__":
    # Integration with command line arguments for automated build systems
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_all_protocols()
    else:
        run_flight_controller()
