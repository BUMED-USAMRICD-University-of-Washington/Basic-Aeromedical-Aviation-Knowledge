# cli_main.py
import sys
import os
import importlib
import time
from export_telemetry import TelemetryDispatcher
from waypoint_manager import WaypointManager
from flight_control_dynamics import FlightControlDynamics

# --- 1. GLOBAL INITIALIZATION ---
# Using src/ directory for local data ingestion
SRC_DIR = "src"
LOG_DIR = "logs"

# Ensure local data infrastructure exists
if not os.path.exists(SRC_DIR):
    print(f"CRITICAL ERROR: {SRC_DIR} directory missing.")
    sys.exit(1)

# Initialize Avionics with local data paths
def initialize_avionics():
    try:
        # Waypoint manager targets local src data
        nav = WaypointManager(dso_catalog_path=os.path.join(SRC_DIR, "catalog-3.23.dat"))
        computer = FlightControlDynamics(mode="CIVILIAN")
        dispatcher = TelemetryDispatcher(output_dir=LOG_DIR)
        print("SYSTEM INITIALIZED: Avionics logic and local src data bridges online.")
        return nav, computer, dispatcher
    except Exception as e:
        print(f"CRITICAL BOOT FAILURE: {e}")
        sys.exit(1)

MODULES = [
    "wind_dynamics", 
    "fog_thermodynamics", 
    "radiation_model", 
    "cloud_model", 
    "space_weather_engine", 
    "lunar_model", 
    "aviation_icing",
    "rossby_model",
    "cloud_temperature_drop",
    "cloud_calendar",
    "aita_model",
    "sfo_model"
]

def verify_modules():
    print("\n--- Verifying Module Integrity ---")
    loaded_modules = {}
    for mod_name in MODULES:
        try:
            loaded_modules[mod_name] = importlib.import_module(mod_name)
            print(f"LOADED: {mod_name}")
        except ImportError as e:
            print(f"FAILED: {mod_name} | Error: {e}")
    return loaded_modules

def run_boeing_master_sequence(loaded_engines, override_data):
    """Executes the engines in strict thermodynamic and physical order."""
    print("\nENGAGING BOEING MASTER PHYSICS SEQUENCE...")
    
    sequence = [
        ("space_weather_engine", "run_space_layer"),
        ("radiation_model", "run_radiation_layer"),
        ("cloud_model", "run_cloud_layer"),
        ("fog_thermodynamics", "run_fog_layer"),
        ("aviation_icing", "run_icing_layer"),
        ("wind_dynamics", "run_wind_layer"),
        ("lunar_model", "run_lunar_layer")
    ]
    
    for mod_name, func_name in sequence:
        if mod_name in loaded_engines:
            engine = loaded_engines[mod_name]
            if hasattr(engine, func_name):
                print(f"Sequence Step: {mod_name}")
                getattr(engine, func_name)(telemetry_override=override_data)
            else:
                print(f"Skipping {mod_name}: Missing {func_name}()")
        else:
            print(f"Skipping {mod_name}: Module failed to load.")
            
    print("\nMASTER SEQUENCE COMPLETE.")

def run_flight_controller():
    nav, computer, dispatcher = initialize_avionics()
    loaded_engines = verify_modules()
    
    # Telemetry Mock Data
    override_data = {
        "temp_c": 15.0, "pressure_hpa": 1013.2, "lat": 47.6062, "lon": -122.3321, 
        "alt": 3000.0, "pitch": 0.0, "roll": 0.0, "yaw": 180.0,
        "grid_data": np.random.rand(10, 10)
    }
    
    while True:
        print("\n==================================================")
        print("Basic Aviation Knowledge - Flight Controller")
        print("==================================================")
        
        active_wp = nav.get_active_waypoint(index=0)
        wp_name = active_wp.name if active_wp else 'None'
        print(f"Active Waypoint: {wp_name}")
        print(f"Dynamics Mode:   {computer.mode}")
        
        if active_wp:
            safety = computer.analyze_maneuver_safety(current_airspeed=110, target_bank_deg=30)
            margin_status = "UNSAFE" if safety['is_unsafe'] else "SAFE"
            print(f"Stall Margin:    {safety['margin']} kts ({margin_status})")

        print("\nAvailable Execution Engines")
        available = list(loaded_engines.keys())
        for i, name in enumerate(available, 1):
            print(f"{i}. Run {name}")
            
        print("\nSystem Commands")
        print("B. Run Boeing Master Physics Sequence")
        print("E. Export Global Multi-Protocol Telemetry")
        print("Q. Quit Application")
        
        choice = input("\nEnter selection: ").strip().upper()
        
        if choice == 'Q':
            print("Shutting down flight controller.")
            sys.exit(0)
            
        elif choice == 'B':
            run_boeing_master_sequence(loaded_engines, override_data)
            
        elif choice == 'E':
            print("\nGenerating Global Payload...")
            # Dispatch to ALL contractors: Boeing, NASA, Lockheed, Axiom, Northrop, OAAM
            dispatcher.dispatch(override_data)
            print("Dispatch Complete.")
            
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(available):
                    selected_mod_name = available[idx]
                    engine = loaded_engines[selected_mod_name]
                    func_name = next((attr for attr in dir(engine) if attr.startswith("run_")), None)
                    
                    if func_name:
                        print(f"Engaging {func_name} in {selected_mod_name}...")
                        getattr(engine, func_name)(telemetry_override=override_data)
                    else:
                        print(f"Error: No orchestration function found in {selected_mod_name}")
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input.")

if __name__ == "__main__":
    try:
        run_flight_controller()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted. Exiting.")
        sys.exit(0)
