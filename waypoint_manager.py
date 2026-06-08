# --- PRIMARY ENGINE: Multi-Domain Waypoint Manager & Tactical Guidance ---
import os
import json
import math
import pandas as pd
import numpy as np
import logging
from pydantic import BaseModel, Field, ValidationError
from atmospheric_entry_controller import AtmosphericEntryController

# --- 1. CONFIGURATION SCHEMA ---
class VehicleSpecs(BaseModel):
    vehicle_mass: float = Field(gt=0)
    wing_area: float = Field(gt=0)
    cd0: float = Field(gt=0)
    induced_drag_k: float = Field(gt=0)
    nose_radius: float = Field(gt=0)

class WaypointManager:
    def __init__(self, config_path="config.json", dso_catalog_path="src/catalog-3.23.dat"):
        self.config_path = config_path
        self.dso_catalog_path = dso_catalog_path
        self.waypoints = []
        self.active_space_target = None
        self.s_turn_enabled = False # Default state: PRO Math
        
    def set_s_turn_mode(self, enabled: bool):
        """Selector toggle for the S-Turn energy management system."""
        self.s_turn_enabled = enabled
        logging.info(f"S-Turn Mode: {'ENABLED' if enabled else 'DISABLED'}")

    def calculate_tactical_approach(self, ship_pos, ship_vel, target_lat, target_lon):
        """
        Tactical Approach Interface.
        Uses Standard Math by default; switches to Energy Management if s_turn_enabled is True.
        """
        # 1. Kinematic Intercept (Standard Math - Preserved)
        intercept = self.calculate_universal_intercept(ship_pos, ship_vel)
        
        # 2. Conditional Energy Management Logic
        if self.s_turn_enabled:
            # Only trigger thermal feasibility check if user enabled the selector
            v_mag = np.linalg.norm(ship_vel)
            alt = np.linalg.norm(ship_pos) - 6371000
            safety = self.entry_controller.evaluate_approach_safety(v=v_mag, h=alt, alpha=35.0)
            
            if not safety['is_safe']:
                return self._inject_s_turn_maneuver(intercept)
        
        # Returns standard intercept if S-Turn is False
        return intercept
        
        # Load and Validate Configuration
        self.config = self._load_and_validate_config()
        
        # Initialize Tactical Entry Controller (Energy Management)
        self.entry_controller = AtmosphericEntryController(
            mass=self.config.vehicle_mass,
            S=self.config.wing_area,
            cd0=self.config.cd0,
            K=self.config.induced_drag_k,
            R_p=6371000, 
            g0=9.81
        )
        self._load_space_catalog()

    def _load_and_validate_config(self) -> VehicleSpecs:
        """Schema validation to prevent illegal physics inputs."""
        if not os.path.exists(self.config_path):
            return VehicleSpecs(vehicle_mass=95000, wing_area=330, cd0=0.028, induced_drag_k=0.042, nose_radius=1.5)
            
        with open(self.config_path, 'r') as f:
            data = json.load(f)
            # Assuming 'Starship_Class' is the active profile
            return VehicleSpecs(**data.get("Starship_Class", {}))

    def calculate_tactical_approach(self, ship_pos, ship_vel, target_lat, target_lon):
        """
        Calculates 3D intercept with integrated energy management.
        If the approach is 'Too Hot', it forces an S-turn trajectory.
        """
        # 1. Kinematic Intercept
        intercept = self.calculate_universal_intercept(ship_pos, ship_vel)
        
        # 2. Thermodynamic Feasibility Check
        v_mag = np.linalg.norm(ship_vel)
        alt = np.linalg.norm(ship_pos) - 6371000
        safety = self.entry_controller.evaluate_approach_safety(v=v_mag, h=alt, alpha=35.0)
        
        # 3. Autonomous Energy Correction
        if not safety['is_safe']:
            logging.warning(f"TACTICAL ALERT: Heat Flux {safety['heat_flux']:.1f} W/cm2. Energy bleed required.")
            return self._inject_s_turn_maneuver(intercept)
            
        return intercept

    def _inject_s_turn_maneuver(self, intercept):
        """Creates lateral bank waypoints to extend flight path without losing speed."""
        intercept['maneuver'] = "S-TURN_ENERGY_BLEED"
        intercept['bank_cmd'] = 45.0 # Command max safe bank to generate lateral drag
        return intercept

    def calculate_universal_intercept(self, ship_pos, ship_vel, target_alt_m=0):
        """Standard 3D Intercept Engine (Core Navigation)."""
        if not self.active_space_target: return None
        
        target_body_pos = self.active_space_target["position_vec"]
        dist_to_core = np.linalg.norm(target_body_pos - np.array(ship_pos))
        closing_vel = np.linalg.norm(ship_vel)
        
        tti = (dist_to_core - self.active_space_target["radius"]) / (closing_vel + 1e-6)
        
        # GPS/Vector Logic
        lat_r, lon_r = math.radians(self.active_space_target["lat"]), math.radians(self.active_space_target["lon"])
        r = self.active_space_target["radius"] + target_alt_m
        
        local_vec = np.array([
            r * math.cos(lat_r) * math.cos(lon_r),
            r * math.cos(lat_r) * math.sin(lon_r),
            r * math.sin(lat_r)
        ])
        
        return {"heading": (target_body_pos - np.array(ship_pos)) / dist_to_core, "tti": tti}

    def _load_space_catalog(self):
        if os.path.exists(self.dso_catalog_path):
            self.dso_database = pd.read_csv(self.dso_catalog_path)
