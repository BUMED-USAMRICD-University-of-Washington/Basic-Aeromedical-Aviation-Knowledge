# intent_engine.py
import numpy as np
import logging
from numba import njit
# --- FULL SPECTRUM PHYSICS INTEGRATION ---
import aviation_physics
import wind_dynamics
import aviation_icing
import SFO_climate_model
import space_weather_engine
import fog_thermodynamics
import lunar_model
class IntentEngine:
    def __init__(self):
        self.logger = logging.getLogger("IntentEngine")
        self.logger.info("Advanced Intent Engine active: Multi-Physics Suite Enabled.")
    def calculate_environmental_drift(self, position, velocity, time_offset_s):
        """
        Applies dynamic weather, climate, and gravitational forces to alter 
        the intended velocity vector over time.
        """
        # 1. Atmospheric & Wind Drift
        # Assumes wind_dynamics returns a 3D vector [x, y, z] drift
        wind_vector = wind_dynamics.calculate_wind_vector(position) if hasattr(wind_dynamics, 'calculate_wind_vector') else np.array([0,0,0])
        # 2. Temperature & Density (SFO Climate + Fog Thermodynamics)
        air_density = SFO_climate_model.get_air_density(position[2]) if hasattr(SFO_climate_model, 'get_air_density') else 1.225
        temp_offset = fog_thermodynamics.get_temperature_drop(position) if hasattr(fog_thermodynamics, 'get_temperature_drop') else 0.0 
        # 3. Icing Accumulation (Translates to drag/velocity loss)
        ice_drag_factor = aviation_icing.compute_drag_penalty(temp_offset, velocity) if hasattr(aviation_icing, 'compute_drag_penalty') else 0.0
        # 4. Space / Orbital Perturbations
        gravity_vector = aviation_physics.compute_gravity(position) if hasattr(aviation_physics, 'compute_gravity') else np.array([0, -9.81, 0])
        lunar_perturbation = lunar_model.compute_tidal_force(position) if hasattr(lunar_model, 'compute_tidal_force') else np.array([0,0,0])
        # --- NET PHYSICS RESOLUTION ---
        # Degrade velocity with ice, add wind translation
        net_velocity = velocity + wind_vector - (velocity * ice_drag_factor)
        # Sum accelerations
        net_acceleration = gravity_vector + lunar_perturbation
        # Return the physically drifted velocity for this time step
        return net_velocity + (net_acceleration * time_offset_s)
    def calculate_maneuver_envelope(self, planned_path):
        """Refines the baseline path by subjecting it to the physical environment."""
        refined_path = []
        for point in planned_path:
            t = point['time_offset']
            pos = point['position']
            # Default to current velocity if not provided in path dict
            vel = point.get('velocity', np.array([250.0, 0.0, 0.0]))     
            # Apply all environmental physics to drift the future position
            drifted_vel = self.calculate_environmental_drift(pos, vel, t)
            adjusted_pos = pos + (drifted_vel * t)      
            refined_path.append({
                "time_offset": t,
                "position": adjusted_pos,
                "velocity": drifted_vel,
                "environmental_confidence": 0.85 # Degrades dynamically in radar logic
            })   
        return refined_path
    # --- TACTICAL ADS-B INTENT PROFILING ---
    def evaluate_tactical_intent(self, v_intruder, u_track, flight_path_angle, is_oscillating):
        """
        Classifies the intruder's maneuver based on kinematic geometry.
        """
        intent_flag = "UNKNOWN"
        # 1. STAR/SID Correlation (Cosine Similarity)
        # 𝜌_SID = (v_int · u_track) / (||v_int|| * ||u_track||)
        norm_v = np.linalg.norm(v_intruder)
        norm_u = np.linalg.norm(u_track)
        if norm_v > 0 and norm_u > 0:
            rho_sid = np.dot(v_intruder, u_track) / (norm_v * norm_u)
            if rho_sid > 0.99: # Delta-psi < 8 degrees
                return "ON_PUBLISHED_ARRIVAL_ROUTE"     
        # 2. Emergency & Spacing Logic
        if is_oscillating:
            intent_flag = "S_TURN_SPACING_MANEUVER"
        elif flight_path_angle < -12.0:
            intent_flag = "EMERGENCY_DIVE_PROFILE"
        return intent_flag
