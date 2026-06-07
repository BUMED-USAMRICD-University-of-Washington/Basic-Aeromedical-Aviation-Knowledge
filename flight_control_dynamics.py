import numpy as np
from waypoint_manager import WaypointManager
class FlightControlDynamics:
    def __init__(self, mode="CIVILIAN"):
        self.mode = mode
        self.dynamic = True
        self.bank_limit = 30.0 if mode == "CIVILIAN" else 60.0
        self.wp_manager = WaypointManager() # Now the engine manages its own navigation data
    def get_dynamics_for_active_waypoint(self, current_heading, current_alt, ground_speed):
        """
        Fetches the current active waypoint and calculates the required attitude.
        """
        active_wp = self.wp_manager.get_active_waypoint(index=0)
        
        if not active_wp:
            return None # No waypoint registered, no correction possible

        return self.calculate_required_attitude(
            current_heading, 
            active_wp.target_heading, 
            active_wp.alt, 
            current_alt, 
            ground_speed
        )
    def get_smooth_heading(self, current_pos, current_heading, ground_speed):
        """
        Calculates the smoothed heading. If near a waypoint, it blends
        the heading toward the next leg.
        """
        active_wp = self.wp_manager.get_active_waypoint(index=0)
        next_wp = self.wp_manager.get_active_waypoint(index=1)
        
        # Calculate distance to current waypoint (Simple Euclidean for now)
        dist = np.sqrt((current_pos['lat'] - active_wp.lat)**2 + 
                       (current_pos['lon'] - active_wp.lon)**2)
        
        # If we are inside the turn radius, interpolate between current and next
        if dist < active_wp.turn_radius and next_wp:
            # Blend factor: 0.0 at edge of radius, 1.0 at waypoint
            blend = 1.0 - (dist / active_wp.turn_radius)
            # Smoothly transition target heading
            return active_wp.target_heading * (1 - blend) + next_wp.target_heading * blend
        
        return active_wp.target_heading
    def calculate_required_attitude(self, current_heading, target_heading, target_elevation, current_alt, ground_speed):
        # 1. Get the smoothed target heading
        target_h = self.get_smooth_heading(current_pos, current_heading, ground_speed)
        
        # 2. Proceed with attitude calc using smoothed heading
        heading_diff = (target_h - current_heading + 180) % 360 - 180
        roll_angle = np.clip(heading_diff * 0.5, -self.bank_limit, self.bank_limit)
        
        # 3. Roll Calculation (Bank angle for turn)
        heading_diff = target_heading - current_heading
        # Normalize heading difference to -180 to 180
        heading_diff = (heading_diff + 180) % 360 - 180
        roll_angle = np.clip(heading_diff * 0.5, -self.bank_limit, self.bank_limit)
        
        # 4. Attitude (Pitch) for Elevation Change
        alt_diff = target_elevation - current_alt
        # Simplified pitch gradient (e.g., 3-degree slope is ~5.2% gradient)
        pitch_angle = np.clip(alt_diff * 0.05, -15, 15)
        
        # 5. Rudder (Coordination)
        rudder = roll_angle * 0.1
        
        return {"roll": roll_angle, "rudder": rudder, "pitch": pitch_angle}

    def set_mode(self, dynamic_on=True, mode="CIVILIAN"):
        self.dynamic = dynamic_on
        self.bank_limit = 30.0 if mode == "CIVILIAN" else 60.0
# Add this method to your FlightControlDynamics class in flight_control_dynamics.py
    def calculate_turn_deceleration(self, weight_lbs, thrust_lbs, velocity_kts, bank_angle_deg):
        """
        Calculates the deceleration (speed bleed) in a banked turn.
        Returns: Speed bleed in Knots Per Second. 
        A negative value indicates the aircraft is slowing down.
        """
        g = 32.2  # ft/s^2
        # Simplified Induced Drag calculation for trim compensation
        # D_induced increases with the square of the Load Factor (n)
        # where n = 1 / cos(bank_angle)
        load_factor = 1.0 / np.cos(np.radians(bank_angle_deg))
        
        # Estimate Drag based on aerodynamic configuration
        # For trim correction, we focus on the delta (change) in drag
        # induced by the turn
        d_parasite = 0.05 * (velocity_kts ** 2) # simplified parasite drag
        d_induced = 0.02 * (velocity_kts ** 2) * (load_factor ** 2) # induced drag spike
        
        # Acceleration formula: dv/dt = (g / W) * (T - D)
        # We convert weight to lbs force units
        dv_dt_fps2 = (g / weight_lbs) * (thrust_lbs - (d_parasite + d_induced))
        
        # Convert to Knots Per Second
        dv_dt_kts_per_sec = dv_dt_fps2 / 1.68781
        
        return dv_dt_kts_per_sec
# Add this to your FlightControlDynamics class
def get_turn_exit_metrics(self, current_v_kts, bank_deg, roc_fpm, thrust_lbs, weight_lbs=2400):
    """
    Calculates exit acceleration and stall safety margin.
    """
    # 1. Compute Load Factor (n)
    rad_bank = np.radians(bank_deg)
    n = 1.0 / np.cos(rad_bank)
    
    # 2. Dynamic Stall Speed (Stall Speed Penalty Multiplier)
    # V_stall_turn = V_stall_level * sqrt(n)
    v_stall_turn = 50.0 * np.sqrt(n) # Assuming 50kts level stall speed
    stall_margin = current_v_kts - v_stall_turn
    
    # 3. Acceleration out of turn (Total Energy Model)
    # Incorporating induced drag increase and gravity vector (Gamma)
    gamma = np.arcsin(roc_fpm / (current_v_kts * 1.688)) # Convert FPM to FPS
    g = 32.2
    
    # Drag estimation (simplified profile)
    d_induced = 0.02 * (current_v_kts**2) * (n**2)
    d_parasite = 0.05 * (current_v_kts**2)
    
    # Acceleration formula: dv/dt = (g/W)*(T - D) - g*sin(gamma)
    accel_fps2 = (g / weight_lbs) * (thrust_lbs - (d_parasite + d_induced)) - (g * np.sin(gamma))
    accel_kts_per_sec = accel_fps2 / 1.6878
    
    return {
        "acceleration_kts_per_sec": round(accel_kts_per_sec, 2),
        "stall_margin_kts": round(stall_margin, 1),
        "is_safe": stall_margin > 10.0 # Warning flag if margin < 10 knots
    }
    # Add this to your FlightControlDynamics class
    def analyze_maneuver_safety(self, current_airspeed, target_bank_deg, v_stall_level=50.0):
        """
        Predicts if a planned maneuver will breach safety margins.
        Returns: { 'is_unsafe': bool, 'margin': float }
        """
        # Calculate Load Factor for the target bank
        rad_bank = np.radians(target_bank_deg)
        n = 1.0 / np.cos(rad_bank) # Load factor formula
        
        # Calculate Dynamic Stall Speed
        v_stall_turn = v_stall_level * np.sqrt(n) # Stall Speed Penalty multiplier
        
        # Calculate Margin (Safety Buffer)
        margin = current_airspeed - v_stall_turn
        
        # Advisory Threshold: 15 knots is a common safety buffer for GA/Commercial envelopes
        # If margin is < 15, we flag it as an "Unsafe Maneuver Plan"
        is_unsafe = margin < 15.0 
        
        return {
            "is_unsafe": is_unsafe,
            "margin": round(margin, 1),
            "stall_speed_turn": round(v_stall_turn, 1)
        }
