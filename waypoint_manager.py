# --- PRIMARY ENGINE: Multi-Domain Waypoint Manager ---
import os
import json
import math
import pandas as pd
from numba import njit

try:
    import cupy as np  # Attempt to use GPU-accelerated array math
    print("🚀 NVIDIA GPU Acceleration Engaged (Waypoint Manager)")
except ImportError:
    import numpy as np # Fallback to standard CPU math
    print("⚡ Using CPU (NVIDIA acceleration not detected)")

# =====================================================================
# TERRESTRIAL AVIATION CLASSES
# =====================================================================
class Waypoint:
    """Standard Atmospheric/Terrestrial Waypoint"""
    def __init__(self, name, lat, lon, alt, target_heading, turn_radius=0.5):
        self.name = name
        self.lat = lat
        self.lon = lon
        self.alt = alt
        self.target_heading = target_heading
        self.turn_radius = turn_radius # NM radius to start the smooth turn

    def to_dict(self):
        return self.__dict__

# =====================================================================
# MULTI-DOMAIN WAYPOINT MANAGER
# =====================================================================
class WaypointManager:
    def __init__(self, config_path="config.json", dso_catalog_path="dso_processed_metrics.csv"):
        # 1. Terrestrial Avionics State
        self.config_path = config_path
        self.waypoints = []
        
        # 2. Space/Kinematic State
        self.dso_catalog_path = dso_catalog_path
        self.dso_database = None
        self.active_space_target = None
        
        # 3. SAFETY INTERLOCK: Defaults to False to prevent atmospheric jets 
        # from accidentally routing to deep space targets.
        self.space_mode_enabled = False 
        
        # Initialize Boot Sequence
        self.load_waypoints()
        self._load_space_catalog()

    # --- SAFETY TOGGLES ---
    def set_space_routing_mode(self, state: bool):
        """
        Manually enables or disables the deep space routing computer.
        Must be True to engage kinematic intercept protocols.
        """
        self.space_mode_enabled = state
        mode_str = "ENGAGED" if state else "DISABLED"
        print(f"\n⚠️ AVIONICS OVERRIDE: Deep Space Routing is now {mode_str}.")
        
        # Clear active space targets if disabled mid-flight
        if not state and self.active_space_target:
            print(f"Aborting space intercept. Dropping lock on: {self.active_space_target['name']}")
            self.active_space_target = None

    # --- TERRESTRIAL ROUTING (Atmospheric) ---
    def register_waypoint(self, name, lat, lon, alt, heading):
        new_wp = Waypoint(name, lat, lon, alt, heading)
        self.waypoints.append(new_wp)
        self.save_waypoints()
        print(f"✅ Registered Terrestrial Waypoint: {name}")

    def save_waypoints(self):
        """Persists terrestrial waypoints to config.json"""
        data = {"waypoints": [wp.to_dict() for wp in self.waypoints]}
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=4)

    def load_waypoints(self):
        """Loads terrestrial waypoints from config.json"""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                data = json.load(f)
                self.waypoints = [Waypoint(**wp) for wp in data.get("waypoints", [])]

    def get_active_waypoint(self, index=0):
        if index < len(self.waypoints):
            return self.waypoints[index]
        return None

    # --- SPACE ROUTING (Kinematic Intercept) ---
    def _load_space_catalog(self):
        """Loads the pre-calculated thermodynamic and mass catalog."""
        if os.path.exists(self.dso_catalog_path):
            self.dso_database = pd.read_csv(self.dso_catalog_path)
            print(f"🛰️ Space Nav Computer online with {len(self.dso_database)} physical targets.")
        else:
            print("⚠️ Space Nav Catalog offline. Awaiting pipeline update.")

    def lock_space_target(self, identifier):
        """
        Locks onto a specific deep sky object by ID or Name. 
        Will reject the command if space_mode_enabled is False.
        """
        # --- SAFETY CHECK ---
        if not self.space_mode_enabled:
            return False, "ROUTING REJECTED: Space Routing Mode is DISABLED. Enable override to target celestial bodies."

        if self.dso_database is None or self.dso_database.empty:
            return False, "Space catalog offline."

        try:
            target_row = self.dso_database[
                (self.dso_database['ID'].astype(str) == str(identifier)) | 
                (self.dso_database['Name'].astype(str).str.contains(str(identifier), case=False, na=False))
            ]
            
            if target_row.empty:
                return False, f"Target {identifier} not found in physics matrix."
                
            target_data = target_row.iloc[0]
            
            self.active_space_target = {
                "id": target_data['ID'],
                "name": target_data.get('Name', f"DSO-{target_data['ID']}"),
                "mass_solar": target_data.get('Estimated_Mass_Solar', 0.0),
                "heat_kelvin": target_data.get('Surface_Temp_Kelvin', 0.0),
                "position_vec": np.array([1.5e11, 0.0, 0.0]), # Example initial JNow pos
                "velocity_vec": np.array([25000.0, -5000.0, 1200.0]) # Example JNow drift
            }
            
            print(f"🎯 SPACE TARGET LOCKED: {self.active_space_target['name']}")
            return True, self.active_space_target
            
        except Exception as e:
            return False, f"Locking error: {str(e)}"

    def calculate_space_interception_route(self, ship_position, ship_velocity):
        """
        Calculates the kinematic intercept vectors to the moving target.
        Returns the required heading vector, closing speed, and Time To Intercept (TTI).
        """
        if not self.space_mode_enabled:
            return None, "Space mode disabled."
            
        if not self.active_space_target:
            return None, "No active space target locked."

        p_ship = np.array(ship_position)
        v_ship = np.array(ship_velocity)
        
        p_target = self.active_space_target["position_vec"]
        v_target = self.active_space_target["velocity_vec"]

        # 1. Relative Distance Vector
        r_rel_vec = p_target - p_ship
        distance_meters = np.linalg.norm(r_rel_vec)
        
        if distance_meters == 0:
            return {"status": "ARRIVED", "distance_m": 0, "tti_seconds": 0}

        heading_unit_vec = r_rel_vec / distance_meters

        # 2. Closing Velocity
        v_rel_vec = v_ship - v_target
        closing_velocity = np.dot(v_rel_vec, heading_unit_vec)

        # 3. Time to Intercept (TTI)
        tti_seconds = float('inf')
        if closing_velocity > 0:
            tti_seconds = distance_meters / closing_velocity

        return {
            "target_name": self.active_space_target['name'],
            "distance_meters": float(distance_meters),
            "required_heading_vector": heading_unit_vec.tolist(),
            "closing_velocity_m_s": float(closing_velocity),
            "time_to_intercept_sec": float(tti_seconds),
            "target_outrunning": bool(closing_velocity <= 0)
        }

    def step_space_simulation(self, dt_seconds):
        """Advances the target's position in space based on its velocity and dt."""
        if self.space_mode_enabled and self.active_space_target:
            displacement = self.active_space_target["velocity_vec"] * dt_seconds
            self.active_space_target["position_vec"] += displacement


# =====================================================================
# EXECUTION BLOCK (Demonstrating the Safety Interlock)
# =====================================================================
if __name__ == "__main__":
    nav = WaypointManager()
    
    print("\n--- 1. Testing Atmospheric Routing ---")
    nav.register_waypoint("KSEA_APPROACH", 47.4480, -122.3088, 3000, 180)
    active_wp = nav.get_active_waypoint(0)
    print(f"Flying to: {active_wp.name} at {active_wp.alt} ft.")
    
    print("\n--- 2. Pilot Accidentally Selects a Galaxy ---")
    success, msg = nav.lock_space_target("Andromeda")
    if not success:
        print(msg)  # This will print the safety rejection message!
        
    print("\n--- 3. Activating Orbital Capable Craft ---")
    nav.set_space_routing_mode(True)
    
    success, msg = nav.lock_space_target("Andromeda")
    if success:
        # We simulate the ship moving fast enough to catch it
        route = nav.calculate_space_interception_route([0,0,0], [85000.0, 0, 0])
        print(f"Target Distance: {route['distance_meters']:.2e} m")
        print(f"Closing Speed:   {route['closing_velocity_m_s']:.2f} m/s")
        print(f"TTI:             {route['time_to_intercept_sec']:.2f} s")
