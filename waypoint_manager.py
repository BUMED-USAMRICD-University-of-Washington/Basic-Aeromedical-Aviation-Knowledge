# --- PRIMARY ENGINE: Aviation Knowledge Waypoint Manager (Production Release) ---
import os
import json
import math
import pandas as pd
import numpy as np
from numba import njit
from astropy.coordinates import EarthLocation, GCRS
from astropy.time import Time, TimeDelta
import astropy.units as u
import logging

# Import your tactical entry/landing engine
from atmospheric_entry_controller import AtmosphericEntryController

class WaypointManager:
    def __init__(self, config_path="config.json", dso_catalog_path="src/catalog-3.23.dat"):
        self.config_path = config_path
        self.dso_catalog_path = dso_catalog_path
        self.config_data = {}
        self.waypoints = []
        self.dso_database = None
        self.active_space_target = None
        self.space_mode_enabled = False 
        
        # Initialize Tactical Entry Engine (Mass 95t, WingArea 330m2)
        self.entry_controller = AtmosphericEntryController(
            mass=95000, S=330, cd0=0.028, K=0.042, R_p=6371000, g0=9.81
        )
        
        self.load_config()
        self.load_waypoints()
        self._load_space_catalog()

    def load_config(self):
        """Loads and validates configuration with schema checks."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config_data = json.load(f)
            # Schema Validation: Ensure critical physics variables are positive
            if self.config_data.get("vehicle_mass", 0) <= 0:
                raise ValueError("CONFIG ERROR: Vehicle mass must be positive.")

    def lock_space_target(self, identifier, lat=None, lon=None):
        """GPS coordinates are MANDATORY for all space objects (except Earth)."""
        if not self.space_mode_enabled:
            return False, "ROUTING REJECTED: Space Routing Mode is DISABLED."

        if identifier.upper() != "EARTH" and (lat is None or lon is None):
            return False, "GPS COORDINATES REQUIRED: Target requires lat/lon for surface intercept."

        target_row = self.dso_database[
            (self.dso_database['ID'].astype(str) == str(identifier)) | 
            (self.dso_database['Name'].astype(str).str.contains(str(identifier), case=False, na=False))
        ]
        
        if target_row.empty: return False, "Target not found in source catalog."
        
        target_data = target_row.iloc[0]
        self.active_space_target = {
            "name": target_data['Name'],
            "radius": target_data.get('Radius_M', 6371000),
            "rot_period": target_data.get('Rotation_Period_S', 86400),
            "lat": lat if identifier.upper() != "EARTH" else 0.0,
            "lon": lon if identifier.upper() != "EARTH" else 0.0,
            "position_vec": np.array([0.0, 0.0, 0.0]) if identifier.upper() == "EARTH" else np.array([1.5e11, 0.0, 0.0]),
            "velocity_vec": np.array([0.0, 0.0, 0.0]) if identifier.upper() == "EARTH" else np.array([25000.0, -5000.0, 1200.0])
        }
        return True, self.active_space_target

    def calculate_tactical_approach(self, ship_pos, ship_vel, target_lat, target_lon):
        """
        Calculates 3D intercept and checks for 'Too Hot' arrival.
        Automatically commands S-turns for energy management if needed.
        """
        # 1. Kinematic Intercept Calculation
        intercept = self.calculate_universal_intercept(ship_pos, ship_vel)
        
        # 2. Safety Check: Is it too hot?
        safety = self.entry_controller.evaluate_approach_safety(
            v=np.linalg.norm(ship_vel), h=np.linalg.norm(ship_pos), alpha=35.0
        )
        
        # 3. Energy Management Correction
        if not safety['is_safe']:
            print("TACTICAL ALERT: EXCESS ENERGY. Initiating S-turn Maneuver.")
            # Adjust the intercept to include energy bleed waypoints
            return self._generate_s_turn_waypoints(intercept, safety['heat_flux'])
            
        return intercept

    def _generate_s_turn_waypoints(self, current_intercept, heat_flux):
        """
        Injects lateral bank waypoints to bleed energy via increased drag 
        without changing final altitude.
        """
        # Mathematical derivation of S-Turn path extension
        extension_factor = heat_flux / 400.0
        return {"maneuver": "S-TURN", "path_extension_km": extension_factor * 100}

    def calculate_universal_intercept(self, ship_pos, ship_vel, target_alt_m=0):
        """Standard 3D Intercept Engine."""
        if not self.active_space_target: return None
        target_body_pos = self.active_space_target["position_vec"]
        closing_vel = np.linalg.norm(ship_vel)
        dist_to_core = np.linalg.norm(target_body_pos - np.array(ship_pos))
        
        tti = (dist_to_core - self.active_space_target["radius"]) / (closing_vel + 1e-6)
        rot_angle = ((2 * math.pi) / self.active_space_target["rot_period"]) * tti
        
        lat_r, lon_r = math.radians(self.active_space_target["lat"]), math.radians(self.active_space_target["lon"])
        r = self.active_space_target["radius"] + target_alt_m
        
        local_vec = np.array([r * math.cos(lat_r) * math.cos(lon_r), r * math.cos(lat_r) * math.sin(lon_r), r * math.sin(lat_r)])
        rot_mat = np.array([[math.cos(rot_angle), -math.sin(rot_angle), 0], [math.sin(rot_angle), math.cos(rot_angle), 0], [0, 0, 1]])
        final_wpt = target_body_pos + np.dot(rot_mat, local_vec)
        
        return {"heading": (final_wpt - np.array(ship_pos)) / np.linalg.norm(final_wpt - np.array(ship_pos)), "tti": tti}

    def _load_space_catalog(self):
        if os.path.exists(self.dso_catalog_path):
            self.dso_database = pd.read_csv(self.dso_catalog_path)
