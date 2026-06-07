# cli_main.py
import sys
import importlib
from waypoint_manager import WaypointManager
# Initialize the manager globally
wp_manager = WaypointManager()

# List of all primary engine modules to verify and load

MODULES = [
    "AITA_spikes", "aita_model", "sfo_model", "sea_model", 
    "phx_model", "ord_model", "rossby_model", "lunar_model", 
    "fog_thermodynamics", "radiation_model", "wind_dynamics", 
    "space_weather_engine", "cloud_model", "cloud_calendar", 
    "cloud_temperature_drop", "aviation_icing"
]

def verify_modules():
    print("✈️ --- Verifying Module Integrity ---")
    loaded_modules = {}
    for mod_name in MODULES:
        try:
            # Dynamically import the module
            loaded_modules[mod_name] = importlib.import_module(mod_name)
            print(f"✅ [LOADED] {mod_name}")
        except ImportError as e:
            print(f"❌ [FAILED] {mod_name} | Error: {e}")
    return loaded_modules

def run_flight_controller():
    # 1. Run the health check
    loaded_engines = verify_modules()
    
    print("\n✈️ Basic Aviation Knowledge - iOS Flight Controller")
    print("--------------------------------------------------")
    print("Select an Engine to Run:")
    
    # Create a simple menu based on successfully loaded modules
    available = list(loaded_engines.keys())
    for i, name in enumerate(available, 1):
        print(f"{i}. {name}")
    
    choice = input("\nEnter engine number (or 'q' to quit): ")
    
    if choice.lower() == 'q':
        return

    try:
        idx = int(choice) - 1
        selected_mod_name = available[idx]
        engine = loaded_engines[selected_mod_name]
        
        # We try to find the run function dynamically
        func_name = next((attr for attr in dir(engine) if attr.startswith("run_")), None)
        
        if func_name:
            print(f"\n🚀 Engaging {func_name} in {selected_mod_name}...")
            getattr(engine, func_name)(telemetry_override=None)
        else:
            print(f"Error: Could not find a 'run_' function in {selected_mod_name}")
            
    except (ValueError, IndexError):
        print("Invalid selection.")

if __name__ == "__main__":
    run_flight_controller()
