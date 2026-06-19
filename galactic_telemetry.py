from dynamic_memory_cache import DynamicMemoryCache
import math
shared_cache = DynamicMemoryCache(percentage=0.25)
import multiprocessing as mp
import telemetry_link
import os
from datetime import datetime
import pandas as pd
import numba
from astropy.coordinates import EarthLocation, ITRS, GCRS, Galactocentric, CartesianRepresentation
from astropy.time import Time
import astropy.units as u
try:
    import cupy as xp
    from numba import dummy_njit as njit
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Matrix Allocation Active (Galactic Telemetry)")
except ImportError:
    import numpy as xp
    from numba import njit
    HAS_GPU = False
    print("CPU Fallback: Numba Vectorization Active (Galactic Telemetry)")
from numba import njit
import json

""" ===================================================================== """
""" --- PURE MATH KERNELS (THE AVIATION MATHEMATICIANS) --- """
""" ===================================================================== """

@njit(fastmath=True)
def compute_lunar_phase_angle(sun_lon_deg, moon_lon_deg):
    """ Calculates the physical phase angle of a planetary body. """
    
    """ HAPPY PATH: Normalize the longitudinal difference to 360 circle """
    phase_angle = (moon_lon_deg - sun_lon_deg) % 360.0
    
    """ GUARD 1: Prevent negative angles """
    if phase_angle < 0.0:
        phase_angle += 360.0
        
    return phase_angle


@njit(fastmath=True)
def compute_illumination_fraction(phase_angle_deg):
    """ Calculates the percentage of the planetary disk reflecting sunlight. """
    
    """ GUARD 1: Full phase """
    if phase_angle_deg == 180.0:
        return 1.0
        
    """ GUARD 2: New phase """
    if phase_angle_deg == 0.0 or phase_angle_deg == 360.0:
        return 0.0
        
    """ HAPPY PATH: F = 0.5 * (1 - cos(phase_angle)) """
    phase_rad = math.radians(phase_angle_deg)
    illumination = 0.5 * (1.0 - math.cos(phase_rad))
    return illumination


@njit(fastmath=True)
def compute_celestial_distance_au(parallax_arcsec):
    """ Converts astronomical parallax into physical distance (Astronomical Units). """
    
    """ GUARD 1: Prevent division by zero or infinite distances """
    if parallax_arcsec <= 0.0001:
        return 999999.0
        
    """ HAPPY PATH: Distance in parsecs = 1 / parallax, convert to AU """
    distance_parsecs = 1.0 / parallax_arcsec
    distance_au = distance_parsecs * 206265.0
    return distance_au


@njit(fastmath=True)
def compute_equatorial_to_cartesian(ra_deg, dec_deg, distance_au):
    """ Converts Right Ascension and Declination into 3D J2000 spatial coordinates. """
    
    """ GUARD 1: Unmeasured deep-space object """
    if distance_au >= 999998.0:
        return 0.0, 0.0, 0.0
        
    """ HAPPY PATH: Spherical to Cartesian projection """
    ra_rad = math.radians(ra_deg)
    dec_rad = math.radians(dec_deg)
    
    x = distance_au * math.cos(dec_rad) * math.cos(ra_rad)
    y = distance_au * math.cos(dec_rad) * math.sin(ra_rad)
    z = distance_au * math.sin(dec_rad)
    
    return x, y, z

""" ===================================================================== """
""" --- THE ORCHESTRATOR (THE ASTROMETRIC MANAGER) --- """
""" ===================================================================== """

class GalacticTelemetryEngine:
    """ Manages deep-space observation tracking and coordinates for the FSM. """
    
    def __init__(self):
        """ 15-Decimal Default Baselines """
        self.AU_TO_METERS = 149597870700.000000000000000

    def process_lunar_telemetry(self, sun_longitude, moon_longitude):
        """ Calculates live lunar illumination for dark-sky mission planning. """
        
        phase_angle = compute_lunar_phase_angle(float(sun_longitude), float(moon_longitude))
        illumination = compute_illumination_fraction(float(phase_angle))
        
        """ Categorize phase via Else-Less Overrides """
        phase_name = "WANING_CRESCENT"
        
        if phase_angle < 180.0: phase_name = "WAXING_GIBBOUS"
        if phase_angle < 90.0: phase_name = "WAXING_CRESCENT"
        if phase_angle > 180.0: phase_name = "WANING_GIBBOUS"
        
        if phase_angle == 0.0: phase_name = "NEW_MOON"
        if phase_angle == 90.0: phase_name = "FIRST_QUARTER"
        if phase_angle == 180.0: phase_name = "FULL_MOON"
        if phase_angle == 270.0: phase_name = "LAST_QUARTER"
        
        payload = {
            "lunar_phase_angle_deg": round(float(phase_angle), 15),
            "illumination_fraction": round(float(illumination), 15),
            "phase_classification": phase_name
        }
        
        """ Broadcast to environmental bus (impacts optical sensor confidence in the dark) """
        telemetry_link.update_global_state("environment", "lunar_illumination", payload)
        return payload

    def process_deep_space_tracking(self, target_id, ra_deg, dec_deg, parallax_arcsec):
        """ Converts telescopic data into physical spatial intercept coordinates. """
        
        dist_au = compute_celestial_distance_au(float(parallax_arcsec))
        x_au, y_au, z_au = compute_equatorial_to_cartesian(float(ra_deg), float(dec_deg), float(dist_au))
        
        """ Scale to standard mission meters """
        x_m = x_au * self.AU_TO_METERS
        y_m = y_au * self.AU_TO_METERS
        z_m = z_au * self.AU_TO_METERS
        
        payload = {
            "target_id": str(target_id),
            "distance_au": round(float(dist_au), 15),
            "j2000_vector_m": [round(float(x_m), 15), round(float(y_m), 15), round(float(z_m), 15)]
        }
        
        """ Broadcast to navigation bus so WaypointManager can track deep-space intercepts """
        telemetry_link.update_global_state("navigation", "active_space_target", payload)
        return payload

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
