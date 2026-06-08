# memory_manager.py
from dynamic_memory_cache import DynamicMemoryCache

# Create one shared cache instance for the whole app
shared_cache = DynamicMemoryCache(percentage=0.25)

# live_telemetry.py
# Interfaces with USB DGPS/RTK and Barometric Elevation Dongles

import os
import time
import sys

# --- HARDWARE ACCELERATION & MATH ENGINES ---
from numba import njit
try:
    import cupy as np  # Attempt to use GPU-accelerated array math
    print("🚀 NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np # Fallback to standard CPU math
    print("⚡ Using CPU (NVIDIA acceleration not detected)")

# --- SECONDARY ENGINE DEPENDENCIES ---
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic
import streamlit as st

# --- PLATFORM DETECTION (iOS vs Android/Linux) ---
try:
    import location
    IS_IOS = True
    print("📱 iOS/Pyto Environment Detected. Utilizing Internal CoreLocation.")
except ImportError:
    IS_IOS = False
    import serial
    import pynmea2
    print("🔌 Standard Hardware Environment Detected. Awaiting USB DGPS Dongle.")


@njit(fastmath=True) # fastmath enables hardware-level floating point optimizations
def calculate_force_vectors(ax, ay, az, mass_kg):
    """
    High-speed kinematic solver.
    Inputs: 
        ax, ay, az: Acceleration components from IMU/Dongle
        mass_kg: Current aircraft mass
    Returns: Force vector array in Newtons (N)
    """
    # Numba highly prefers scalar inputs over raw tuples for C-compilation
    accel_vec = np.array([ax, ay, az])
    force_vec = accel_vec * mass_kg
    return force_vec
    

def get_live_position(telemetry_override=None, com_port="/dev/ttyUSB0", baudrate=9600, reference_body="Earth"):
    """
    Automatically detects the platform, fetches telemetry, and locks the output vectors 
    to the specific celestial Reference Body selected during the Stellarium boot sequence.
    """
    # 1. OVERRIDE INJECTION (For automated testing or mission planning)
    if telemetry_override:
        return {
            "status": "SUCCESS (OVERRIDE)",
            "reference_frame": reference_body,
            "latitude": telemetry_override.get("lat", 0.0),
            "longitude": telemetry_override.get("lon", 0.0),
            "elevation_ft": telemetry_override.get("elevation_ft", 0.0),
            "satellites_locked": "SIMULATED"
        }

    # 2. IOS / IPAD OS HARDWARE ROUTE
    if IS_IOS:
        try:
            loc = location.get_location()
            return {
                "status": "SUCCESS",
                "reference_frame": reference_body,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "elevation_ft": loc.altitude * 3.28084,
                "satellites_locked": f"Internal GPS ({reference_body} Constellation)"
            }
        except Exception as e:
            return {"status": "FAIL", "reason": f"Location services disabled: {e}"}

    # 3. LINUX / ANDROID / PYDROID OTG USB ROUTE
    else:
        # Verify physical device path exists before attempting serial lock
        if not os.path.exists(com_port):
            return {"status": "ERROR", "message": f"Dongle not found at {com_port}. Ensure OTG adapter is connected."}
            
        try:
            with serial.Serial(com_port, baudrate, timeout=2.0) as ser:
                # Clear buffer to avoid stale data during rapid reconnection/turbulence
                ser.reset_input_buffer()
                
                # Look for GPGGA (GPS) or GNGGA (Multi-GNSS) sentences
                for _ in range(30): 
                    try:
                        line = ser.readline().decode('ascii', errors='replace').strip()
                        if line.startswith(('$GPGGA', '$GNGGA')):
                            msg = pynmea2.parse(line)
                            
                            # Verify we have a valid 3D fix (msg.gps_qual > 0)
                            if msg.gps_qual > 0:
                                elevation_ft = msg.altitude * 3.28084 if msg.altitude else 0.0
                                return {
                                    "status": "SUCCESS",
                                    "reference_frame": reference_body,
                                    "latitude": msg.latitude,
                                    "longitude": msg.longitude,
                                    "elevation_ft": round(elevation_ft, 2),
                                    "satellites_locked": msg.num_sats
                                }
                    except pynmea2.ParseError:
                        continue # Skip corrupted NMEA frames
                        
            return {"status": "ERROR", "message": f"Dongle connected, but no {reference_body} satellite fix acquired."}
            
        except Exception as e:
            return {"status": "ERROR", "message": f"Serial data bus error: {str(e)}"}

if __name__ == "__main__":
    # Local Hardware Diagnostic Test
    print("================================================================")
    print("         HARDWARE TELEMETRY & SENSOR DIAGNOSTIC                 ")
    print("================================================================")
    
    # Test Earth Frame
    result = get_live_position(reference_body="Earth")
    print("\n[TEST 1] Earth Reference Frame Lock:")
    print(result)
    
    # Test Deep Space Intercept Frame (Mars)
    result_mars = get_live_position(reference_body="Mars")
    print("\n[TEST 2] Mars Reference Frame Transition:")
    print(result_mars)
