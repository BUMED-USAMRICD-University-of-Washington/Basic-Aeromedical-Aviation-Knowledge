from dynamic_memory_cache import DynamicMemoryCache
shared_cache = DynamicMemoryCache(percentage=0.25)
import multiprocessing as mp
import os
from datetime import datetime
import pandas as pd
import numba
from astropy.coordinates import EarthLocation, ITRS, GCRS, Galactocentric, CartesianRepresentation
from astropy.time import Time
import astropy.units as u
try:
    import cupy as np
    print("NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np
    print("Using CPU (NVIDIA acceleration not detected)")
from numba import njit
import json
class GalacticFlightTracker:
    """
    Translates standard terrestrial GPS/Avionics telemetry into 
    3D Galactocentric coordinates relative to the Milky Way's center.
    Logs output for FAA/Space-Routing compliance.
    """
    @njit(fastmath=True)
    def __init__(self, log_file="faa_galactic_flight_log.json"):
        self.log_file = log_file
        self.flight_data = []   
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r") as f:
                    self.flight_data = json.load(f)
            except json.JSONDecodeError:
                self.flight_data = []
    @njit(fastmath=True)
    def log_waypoint(self, callsign: str, lat_deg: float, lon_deg: float, alt_meters: float, heading: float, speed_knots: float):
        """
        Takes a terrestrial GPS ping, converts it to deep space coordinates,
        and appends it to the master flight log.
        """
        current_time = Time.now()
        aircraft_loc = EarthLocation.from_geodetic(
            lat=lat_deg * u.deg, 
            lon=lon_deg * u.deg, 
            height=alt_meters * u.m
        )
        itrs_pos = ITRS(
            x=aircraft_loc.x, 
            y=aircraft_loc.y, 
            z=aircraft_loc.z, 
            obstime=current_time
        )
        gcrs_pos = itrs_pos.transform_to(GCRS(obstime=current_time))
        galactocentric_pos = gcrs_pos.transform_to(Galactocentric())
        x_pc = galactocentric_pos.x.to(u.pc).value
        y_pc = galactocentric_pos.y.to(u.pc).value
        z_pc = galactocentric_pos.z.to(u.pc).value
        pc_to_m = 3.08567758128e16
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
    @njit(fastmath=True)
    def _write_log(self):
        """Safely flushes the flight log to disk."""
        with open(self.log_file, "w") as f:
            json.dump(self.flight_data, f, indent=4)
    @njit(fastmath=True)
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
if __name__ == "__main__":
    print("================================================================")
    print("          GALACTIC TELEMETRY & FLIGHT TRACKING ENGINE           ")
    print("================================================================")
    tracker = GalacticFlightTracker()
    print("\n[SYSTEM] Simulating initial terrestrial departure sequence...")
    frame_1 = tracker.log_waypoint(
        callsign="VesselArrest-1",
        lat_deg=47.4480,    
        lon_deg=-122.3088,  
        alt_meters=131.0,     
        heading=180.0,
        speed_knots=150.0
    )
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
