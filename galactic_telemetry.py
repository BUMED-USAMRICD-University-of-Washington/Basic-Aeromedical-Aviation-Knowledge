# memory_manager.py
from dynamic_memory_cache import DynamicMemoryCache

# Create one shared cache instance for the whole app
shared_cache = DynamicMemoryCache(percentage=0.25)

import multiprocessing as mp
# --- PRIMARY ENGINE: Galactic Telemetry & FAA Flight Logging ---
import os
import json
from datetime import datetime
import pandas as pd
import numpy as np

# Astropy for high-precision frame transformations
from astropy.coordinates import EarthLocation, ITRS, GCRS, Galactocentric, CartesianRepresentation
from astropy.time import Time
import astropy.units as u

try:
    import cupy as np  # Attempt to use GPU-accelerated array math
    print("NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np # Fallback to standard CPU math
    print("Using CPU (NVIDIA acceleration not detected)")

class GalacticFlightTracker:
    """
    Translates standard terrestrial GPS/Avionics telemetry into 
    3D Galactocentric coordinates relative to the Milky Way's center.
    Logs output for FAA/Space-Routing compliance.
    """
    def __init__(self, log_file="faa_galactic_flight_log.json"):
        self.log_file = log_file
        self.flight_data = []
        
        # Load existing log if appending to an ongoing flight
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r") as f:
                    self.flight_data = json.load(f)
            except json.JSONDecodeError:
                self.flight_data = []

    def log_waypoint(self, callsign: str, lat_deg: float, lon_deg: float, alt_meters: float, heading: float, speed_knots: float):
        """
        Takes a terrestrial GPS ping, converts it to deep space coordinates,
        and appends it to the master flight log.
        """
        # 1. Capture exact epoch
        current_time = Time.now()
        
        # 2. Define Earth Location (WGS84 Ellipsoid standard for GPS)
        # Using exact elevation to ensure Z-axis accuracy in space
        aircraft_loc = EarthLocation.from_geodetic(
            lat=lat_deg * u.deg, 
            lon=lon_deg * u.deg, 
            height=alt_meters * u.m
        )

        # 3. Transform to ITRS (International Terrestrial Reference System)
        # This gives us X, Y, Z from the center of the Earth, rotating with the Earth.
        itrs_pos = ITRS(
            x=aircraft_loc.x, 
            y=aircraft_loc.y, 
            z=aircraft_loc.z, 
            obstime=current_time
        )

        # 4. Transform to GCRS (Geocentric Celestial Reference System)
        # This detaches the coordinate from Earth's rotation, fixing it to the stars.
        gcrs_pos = itrs_pos.transform_to(GCRS(obstime=current_time))
        
        # 5. Transform to Galactocentric
        # Origin (0,0,0) is Sagittarius A*. 
        galactocentric_pos = gcrs_pos.transform_to(Galactocentric())

        # Extract the XYZ vectors in Parsecs and Meters
        x_pc = galactocentric_pos.x.to(u.pc).value
        y_pc = galactocentric_pos.y.to(u.pc).value
        z_pc = galactocentric_pos.z.to(u.pc).value
        
        # 1 Parsec is approx 3.086e+16 meters
        pc_to_m = 3.08567758128e16

        # Compile FAA / Space Command Telemetry Payload
        telemetry_frame = {
            "timestamp_utc": current_time.iso,
            "callsign": callsign,
            "terrestrial_telemetry": {
                "latitude": lat_deg,
                "longitude": lon_deg,
                "altitude_meters": alt_meters,
                "heading_deg": heading,
                "speed_knots": speed_knots
            },
            "galactic_telemetry_parsecs": {
                "x_pc": x_pc,
                "y_pc": y_pc,
                "z_pc": z_pc
            },
            "galactic_telemetry_meters": {
                "x_m": x_pc * pc_to_m,
                "y_m": y_pc * pc_to_m,
                "z_m": z_pc * pc_to_m
            }
        }

        self.flight_data.append(telemetry_frame)
        self._write_log()

        return telemetry_frame

    def _write_log(self):
        """Safely flushes the flight log to disk."""
        with open(self.log_file, "w") as f:
            json.dump(self.flight_data, f, indent=4)
   
    def export_to_csv(self, csv_filename="galactic_flight_path.csv"):
        """Exports the 3D path for integration with data visualization tools."""
        if not self.flight_data:
            return False

        flat_data = []
        for frame in self.flight_data:
            flat_data.append({
                "time": frame["timestamp_utc"],
                "lat": frame["terrestrial_telemetry"]["latitude"],
                "lon": frame["terrestrial_telemetry"]["longitude"],
                "alt_m": frame["terrestrial_telemetry"]["altitude_meters"],
                "gal_x_pc": frame["galactic_telemetry_parsecs"]["x_pc"],
                "gal_y_pc": frame["galactic_telemetry_parsecs"]["y_pc"],
                "gal_z_pc": frame["galactic_telemetry_parsecs"]["z_pc"]
            })

        df = pd.DataFrame(flat_data)
        df.to_csv(csv_filename, index=False)
        print(f"Exported 3D Flight Path to {csv_filename}")
        return True

# ==========================================
# Execution Block: Flight Logging Test
# ==========================================
if __name__ == "__main__":
    print("================================================================")
    print("          GALACTIC TELEMETRY & FLIGHT TRACKING ENGINE           ")
    print("================================================================")

    # Initialize the tracker
    tracker = GalacticFlightTracker()

    print("\n[SYSTEM] Simulating initial terrestrial departure sequence...")

    # Frame 1: Ground Level 
    frame_1 = tracker.log_waypoint(
        callsign="VesselArrest-1",
        lat_deg=47.4480,    
        lon_deg=-122.3088,  
        alt_meters=131.0,     
        heading=180.0,
        speed_knots=150.0
    )

    # Frame 2: Ascending (Simulating exactly 1 minute later, moving south, climbing)
    frame_2 = tracker.log_waypoint(
        callsign="VesselArrest-1",
        lat_deg=47.3480,    
        lon_deg=-122.3088,  
        alt_meters=3500.0,    
        heading=180.0,
        speed_knots=320.0
    )

    print(f"\n Waypoint 1 Logged (T=0): {frame_1['timestamp_utc']}")
    print(f"   GPS:   {frame_1['terrestrial_telemetry']['latitude']}°, {frame_1['terrestrial_telemetry']['longitude']}° | Alt: {frame_1['terrestrial_telemetry']['altitude_meters']}m")
    print(f"   Gal X: {frame_1['galactic_telemetry_parsecs']['x_pc']:.4f} pc")
    print(f"   Gal Y: {frame_1['galactic_telemetry_parsecs']['y_pc']:.4f} pc")
    print(f"   Gal Z: {frame_1['galactic_telemetry_parsecs']['z_pc']:.4f} pc")

    print(f"\n Waypoint 2 Logged (T+1): {frame_2['timestamp_utc']}")
    print(f"   GPS:   {frame_2['terrestrial_telemetry']['latitude']}°, {frame_2['terrestrial_telemetry']['longitude']}° | Alt: {frame_2['terrestrial_telemetry']['altitude_meters']}m")
    print(f"   Gal X: {frame_2['galactic_telemetry_parsecs']['x_pc']:.4f} pc")
    print(f"   Gal Y: {frame_2['galactic_telemetry_parsecs']['y_pc']:.4f} pc")
    print(f"   Gal Z: {frame_2['galactic_telemetry_parsecs']['z_pc']:.4f} pc")
    
    print("\n[SYSTEM] Generating FAA compliance log and CSV visualization matrix...")
    tracker.export_to_csv()
