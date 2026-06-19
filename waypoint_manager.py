""" waypoint_manager.py """
""" Multi-Domain Waypoint Manager, FSM Tracker, & Intercept Guidance """
""" Optimized: Else-Less Guard Clauses | 15-Decimal Precision | Numba Kernels """
import sys
import math
import multiprocessing as mp
import os
import json
import telemetry_link
from pydantic import BaseModel, Field, ValidationError
from atmospheric_entry_controller import EntryController
from aviation_physics import compute_jit_3d_and_fuel_metrics
from export_telemetry import encode_to_1553b_avionics_bus
from ai_pirep import verbalize_copilot_fuel_announcement
""" --- HARDWARE ABSTRACTION LAYER (HAL) --- """
try:
    import cupy as xp
    from numba import dummy_njit as njit
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Matrix Allocation Active (Waypoint Manager)")
except ImportError:
    import numpy as xp
    from numba import njit
    HAS_GPU = False
    print("CPU Fallback: Numba Vectorization Active (Waypoint Manager)")

""" ===================================================================== """
""" --- PURE MATH KERNELS (THE BASEMENT MATHEMATICIANS) --- """
""" ===================================================================== """
@njit(fastmath=True)
    def calculate_unified_3d_guidance(self, aircraft_telemetry, target_wp_dict, target_altitude, wind_profile, weight_category="medium"):
        """
        Orchestrates, maps, and executes the integrated multi-axis 3D tracking calculation.
        """
        # Assemble Numba-compliant arrays from raw parameter models
        current_state_arr = np.array([
            aircraft_telemetry["lat"],
            aircraft_telemetry["lon"],
            aircraft_telemetry["altitude_ft"],
            aircraft_telemetry["tas_knots"],
            aircraft_telemetry["heading_deg"]
        ], dtype=np.float64)
        
        target_wp_arr = np.array([
            target_wp_dict["lat"],
            target_wp_dict["lon"]
        ], dtype=np.float64)
        
        wind_vector_arr = np.array([
            wind_profile["direction_deg"],
            wind_profile["speed_kts"]
        ], dtype=np.float64)
        
        # Pull performance parameters mapped for aircraft class
        perf_limits = self.active_aircraft_perf.get(weight_category.lower(), self.active_aircraft_perf["medium"])
        
        # Execute unified loop pass
        unified_guidance_out = compute_jit_3d_unified_guidance(
            current_state=current_state_arr,
            horizontal_waypoint=target_wp_arr,
            target_altitude=float(target_altitude),
            performance_limits=perf_limits,
            wind_vector=wind_vector_arr
        )
        
        return {
            "commanded_vertical_speed_fpm": unified_guidance_out[0],
            "commanded_autopilot_heading_deg": unified_guidance_out[1],
            "resolved_crosswind_component_kts": unified_guidance_out[2]
        }

@njit(fastmath=True)
def calculate_spatial_distance(lat1, lon1, alt1, lat2, lon2, alt2):
    """ Fast 3D Haversine-style spatial distance calculation in meters. """
    R = 6371000.0
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    horizontal_distance = R * c
    vertical_distance = alt2 - alt1
    
    total_distance = math.sqrt(horizontal_distance**2 + vertical_distance**2)
    return total_distance
    
    @njit(fastmath=True)
    def process_dynamic_pattern_shear(self, ac_telemetry, live_wind_profile, dt=1.0, weight_category="medium"):
        """
        Intercepts current frame data, injects history records, and returns
        stabilized holding turn limits under dynamic microburst/shear hazards.
        """
        # Maintain a rolling wind frame memory inside the runtime instance object
        if not hasattr(self, "historical_wind_cache"):
            self.historical_wind_cache = {
                "direction_deg": live_wind_profile["direction_deg"],
                "speed_kts": live_wind_profile["speed_kts"]
            }
            
        # Assemble standard primitive arrays for Numba boundary execution
        current_state = np.array([ac_telemetry["lat"], ac_telemetry["lon"], ac_telemetry["alt_ft"], ac_telemetry["tas_kts"], ac_telemetry["hdg_deg"]], dtype=np.float64)
        wind_vector   = np.array([live_wind_profile["direction_deg"], live_wind_profile["speed_kts"]], dtype=np.float64)
        last_wind     = np.array([self.historical_wind_cache["direction_deg"], self.historical_wind_cache["speed_kts"]], dtype=np.float64)
        
        # Max safe bank parameters appended [Climb, Descent, GlideAngle, MaxAirframeBank]
        # Heavy transport aircraft are limited to 25° standard holding banks; Military tactical up to 45°
        perf_map = {
            "light":    np.array([1000.0, 1500.0, 3.0, 30.0], dtype=np.float64),
            "medium":   np.array([2500.0, 3000.0, 3.0, 25.0], dtype=np.float64),
            "heavy":    np.array([4000.0, 4500.0, 3.0, 25.0], dtype=np.float64),
            "military": np.array([9000.0, 8000.0, 4.5, 45.0], dtype=np.float64)
        }
        perf_limits = perf_map.get(weight_category.lower(), perf_map["medium"])
        
        # Execute JIT compiled shear tracking module
        shear_telemetry_bus = compute_jit_wind_shear_turn_correction(
            current_state=current_state,
            wind_vector=wind_vector,
            last_wind_vector=last_wind,
            dt=float(dt),
            base_perf_limits=perf_limits
        )
        
        # Commit current wind data to the rolling history frame for next epoch loop iteration
        self.historical_wind_cache["direction_deg"] = live_wind_profile["direction_deg"]
        self.historical_wind_cache["speed_kts"] = live_wind_profile["speed_kts"]
        
        return {
            "measured_shear_gradient_kts_sec": shear_telemetry_bus[0],
            "computed_safe_turn_radius_meters": shear_telemetry_bus[1],
            "commanded_bank_angle_degrees": shear_telemetry_bus[2],
            "structural_limit_override_engaged": bool(shear_telemetry_bus[3])
        }

    @njit(fastmath=True)
    def monitor_holding_efficiency(self, current_fuel_lbs, aircraft_type, altitude_ft, bank_angle_deg, destination_diversion_fuel_lbs=1500.0):
        """
        Evaluates real-time fuel efficiency to protect the aircraft's safety margins.
        Automatically adds the FAA legal reserve fuel requirement to diversion calculations.
        """
        # 1. Dynamically evaluate the current fuel flow rate
        fuel_flow_pph = self.geo_engine.calculate_holding_fuel_flow(
            weight_category=aircraft_type,
            altitude_ft=altitude_ft,
            bank_angle_deg=bank_angle_deg
        )
        
        # 2. Enforce FAA Legal Reserves (45 minutes of fuel for IFR operations)
        faa_legal_reserve_lbs = (fuel_flow_pph / 60.0) * 45.0
        
        # Total absolute structural safety floor (Bingo Fuel threshold)
        total_required_reserve = destination_diversion_fuel_lbs + faa_legal_reserve_lbs
        
        # 3. Calculate holding time limits
        endurance_mins, alert_msg = self.geo_engine.evaluate_hold_time_limits(
            current_fuel_lbs=current_fuel_lbs,
            reserve_fuel_lbs=total_required_reserve,
            fuel_flow_pph=fuel_flow_pph
        )
        
        return {
            "calculated_fuel_flow_pph": round(fuel_flow_pph, 1),
            "faa_45min_reserve_requirement_lbs": round(faa_legal_reserve_lbs, 1),
            "total_bingo_fuel_threshold_lbs": round(total_required_reserve, 1),
            "remaining_hold_endurance_minutes": round(endurance_mins, 1),
            "safety_assessment": alert_msg,
            "fuel_status_critical": current_fuel_lbs <= total_required_reserve
        }

@njit(fastmath=True)
def ekf_prediction_step(x_hat, u, P, Q, dt):
    """ Non-linear State-Space EKF projection for Ground Tracking. """
    
    """ GUARD 1: Prevent negative or zero time skips """
    if dt <= 0.0:
        return x_hat, P

    """ HAPPY PATH: Euler Integration """
    forward_accel = u[0]
    yaw_accel = u[1]
    
    x_prior = xp.copy(x_hat)
    x_prior[2] = x_hat[2] + (forward_accel * dt)
    x_prior[3] = x_hat[3] + (yaw_accel * dt)
    x_prior[0] = x_hat[0] + (x_prior[2] * math.cos(x_prior[3]) * dt)
    x_prior[1] = x_hat[1] + (x_prior[2] * math.sin(x_prior[3]) * dt)
    
    F = xp.eye(6)
    F[0, 2] = math.cos(x_prior[3]) * dt
    F[1, 2] = math.sin(x_prior[3]) * dt
    F[0, 3] = -x_prior[2] * math.sin(x_prior[3]) * dt
    F[1, 3] = x_prior[2] * math.cos(x_prior[3]) * dt
    
    P_prior = (F @ P @ F.T) + Q
    return x_prior, P_prior

@njit(fastmath=True)
def compute_intercept_metrics(sx, sy, sz, vx, vy, vz, tx, ty, tz, target_radius_m):
    """ Calculates absolute distance and Time-To-Intercept (TTI). """
    dist_to_core = math.sqrt((tx - sx)**2 + (ty - sy)**2 + (tz - sz)**2)
    closing_vel = math.sqrt(vx**2 + vy**2 + vz**2)
    
    """ GUARD 1: No velocity (Stationary) """
    if closing_vel <= 0.0:
        return dist_to_core, 999999.0
        
    """ HAPPY PATH """
    tti = (dist_to_core - target_radius_m) / closing_vel
    return dist_to_core, tti


""" ===================================================================== """
""" --- THE PYDANTIC FIREWALL --- """
""" ===================================================================== """

class VehicleSpecs(BaseModel):
    """ Enforces strict physics boundaries on JSON configurations. """
    vehicle_mass_kg: float = Field(gt=0.0)
    wing_area_m2: float = Field(gt=0.0)
    cd0: float = Field(gt=0.0)
    induced_drag_k: float = Field(gt=0.0)
    nose_radius_m: float = Field(gt=0.0)
    max_thrust_n: float = Field(default=250000.000000000000000, gt=0.0)


""" ===================================================================== """
""" --- THE ORCHESTRATOR (THE MANAGER) --- """
""" ===================================================================== """
"""
Root Waypoint Manager Facade.
Orchestrates high-level automation requests, maps system inputs to low-level 
geometric models inside src/, and interfaces directly with database and simulation loops.
"""
def get_numba_compatible_waypoints(self, telemetry_output):
    """Converts standard dictionary waypoints into flat NumPy arrays for Numba."""
    points = telemetry_output["generated_waypoint_stack"]
    return np.array([[wp["lat"], wp["lon"]] for wp in points], dtype=np.float64)

# Ensure project src directory is available in the path context
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import the foundational mathematical engine we just updated
from waypoint_manager import WaypointManager as GeometricEngine

class RootWaypointManager:
    def __init__(self, airport_db_path="src/airports_db.json"):
        self.geo_engine = GeometricEngine()
        self.airport_db = self._load_airport_database(airport_db_path)
        #self.geo_engine = WaypointManager()
        #self.airport_db = {"KSEA": {"center_lat": 47.4489, "center_lon": -122.3093, "runways": {"16L/34R": {"heading": 340.0, "length_feet": 11901.0}}}}
        # Cache for managing internal aircraft data types
        self.active_aircraft_perf = {
            "light":      np.array([1000.0, 1500.0, 3.0], dtype=np.float64),  # [MaxClimb, MaxDescent, GlideAngle]
            "medium":     np.array([2500.0, 3000.0, 3.0], dtype=np.float64),
            "heavy":      np.array([4000.0, 4500.0, 3.0], dtype=np.float64),
            "military":   np.array([9000.0, 8000.0, 4.5], dtype=np.float64)   # Tactical high-performance specs
        }

    def pipe_holding_altitude_to_jit_loop(self, current_altitude, current_speed, selected_faa_level, weight_category="medium"):
        """
        Extracts complex Python configuration types and feeds them directly 
        as primitive, continuous float64 parameters into Numba's memory space.
        """
        # 1. Unpack aircraft telemetry into a strict 1D NumPy array format
        current_state_array = np.array([0.0, 0.0, current_altitude, current_speed], dtype=np.float64)
        
        # 2. Select matching structural performance arrays
        perf_limits = self.active_aircraft_perf.get(weight_category.lower(), self.active_aircraft_perf["medium"])
        
        # 3. Direct pass down across boundaries into the accelerated compiled code block
        commanded_vs, altitude_error = compute_jit_vertical_guidance(
            current_state=current_state_array,
            target_altitude=float(selected_faa_level),
            performance_limits=perf_limits
        )
        
        return commanded_vs, altitude_error

    def initialize_dimension_aware_hold(self, airport_id, rwy_id, raw_adsb_feed):
        """
        Prompts crew for structural weight details and course rules,
        then displays up to 7 precisely sliced legal options instead of the middle.
        """
        apt = self.airport_db[airport_id]
        rwy_heading = self.airport_db[airport_id]["runways"][rwy_id]["heading"]
        
        print("\n========================================================")
        print(f"       FAA LEGAL AIRSPACE FLIGHT-LEVEL CONFIGURATOR     ")
        print("========================================================")
        
        # Interactive prompts to feed the sizing calculations
        weight_cat = input("Enter Aircraft Weight Category (light/medium/heavy): ").lower() or "medium"
        wingspan_m = float(input("Enter Aircraft Wingspan in meters: ") or "36.0")
        flight_rules = input("Enter operational Flight Rules (IFR/VFR): ").upper() or "IFR"
        
        # Run slicing math
        available_slices = self.geo_engine.slice_free_space_into_legal_tiers(
            raw_adsb_feed=raw_adsb_feed,
            center_lat=apt["center_lat"],
            center_lon=apt["center_lon"],
            inbound_course=rwy_heading,
            flight_rules=flight_rules,
            weight_cat=weight_cat,
            wingspan_m=wingspan_m
        )
        
        print(f"\n[FAA RESOLUTION] Legally Sliced Slices for Holding Inbound Heading ({rwy_heading}°):")
        for idx, opt in enumerate(available_slices, 1):
            print(f"  [{idx}] -> Flight Level: {opt['altitude_ft']} ft | Envelope: {opt['span_clearance']} | ({opt['faa_rule_match']})")
            
        selection = int(input("\nSelect specific legal tier index (1-7): ") or "1")
        final_tier = available_slices[selection - 1]["altitude_ft"]
        
        print(f"\n[SUCCESS] Locked into legal FAA Flight Level: {final_tier} feet.")
        return final_tier        
        # State tracker to manage the aircraft's active real-time flight profile
        self.active_flight_profile = {
            "target_airport": None,
            "target_runway": None,
            "assigned_holding_altitude": 5000, # Default safe baseline entry
            "atc_override_active": False
        }
    def execute_unified_system_pass(self, ac_telemetry, target_wp, assigned_faa_alt, wind_profile, fuel_telemetry):
        """
        Executes a single fully unified system loop pass.
        Math is JIT-accelerated, outputs are sent to the 1553B bus, and audio is prioritized.
        """
        # 1. Unpack aircraft telemetry into primitive float64 data arrays
        current_state = np.array([ac_telemetry["lat"], ac_telemetry["lon"], ac_telemetry["alt_ft"], ac_telemetry["tas_kts"], ac_telemetry["hdg_deg"]], dtype=np.float64)
        horizontal_wp = np.array([target_wp["lat"], target_wp["lon"]], dtype=np.float64)
        wind_vector   = np.array([wind_profile["dir_deg"], wind_profile["spd_kts"]], dtype=np.float64)
        fuel_state    = np.array([fuel_telemetry["current_lbs"], fuel_telemetry["diversion_lbs"], fuel_telemetry["current_bank_deg"]], dtype=np.float64)
        
        perf_limits = self.PERF_MAP.get(ac_telemetry["class"].lower(), self.PERF_MAP["medium"])

        # 2. RUN HIGH-SPEED JIT EXECUTION PASS
        jit_metrics_bus = compute_jit_3d_and_fuel_metrics(
            current_state=current_state,
            horizontal_waypoint=horizontal_wp,
            target_altitude=float(assigned_faa_alt),
            performance_limits=perf_limits,
            wind_vector=wind_vector,
            fuel_state=fuel_state
        )

        # 3. CONVERT AND STREAM RAW BINARY TO MIL-STD-1553B BUS
        binary_1553b_word_packet = encode_to_1553b_avionics_bus(jit_metrics_bus)
        
        # 4. DISPATCH SYNTHESIZED CO-PILOT RADIO CHECK OUTBOUND
        endurance_mins = jit_metrics_bus[5]
        is_critical = (endurance_mins <= 5.0)
        
        verbalize_copilot_fuel_announcement(
            endurance_minutes=endurance_mins,
            fuel_flow_pph=jit_metrics_bus[3],
            bingo_threshold=jit_metrics_bus[4],
            is_critical=is_critical
        )

        return {
            "raw_1553b_binary_stream": binary_1553b_word_packet,
            "vertical_speed_command": jit_metrics_bus[0],
            "crab_heading_command": jit_metrics_bus[1],
            "hold_endurance_remaining_minutes": endurance_mins
        }

# Execution Test Harness
if __name__ == "__main__":
    manager = RootWaypointManager()
    
    # Input datasets simulating normal holding operations
    aircraft = {"class": "medium", "lat": 47.448, "lon": -122.309, "alt_ft": 9000.0, "tas_kts": 180.0, "hdg_deg": 340.0}
    waypoint = {"lat": 47.474, "lon": -122.296}
    wind     = {"dir_deg": 270.0, "spd_kts": 25.0}
    fuel     = {"current_lbs": 4800.0, "diversion_lbs": 1500.0, "current_bank_deg": 15.0}
    faa_alt  = 6000.0 # Sliced level
    
    # Fire unified system loop pass
    bus_result = manager.execute_unified_system_pass(aircraft, waypoint, faa_alt, wind, fuel)
    
    print("\n----------------- LIVE CONSOLE TELEMETRY BUS VERIFICATION -------------")
    print(f"Hex Bus Output String : {bus_result['raw_1553b_binary_stream'].hex().upper()}")
    print(f"JIT Autopilot VS Rate : {bus_result['vertical_speed_command']:.1f} FPM")
    print(f"JIT Autopilot Heading : {bus_result['crab_heading_command']:.2f}°")
    print(f"Minutes to Bingo Fuel : {bus_result['hold_endurance_remaining_minutes']:.1f} Mins")
    def _load_airport_database(self, path):
        """Loads planetary-anchored airport data tied to Stellarium objects."""
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        # Fallback Mock Structure if database needs construction
        return {
            "KSEA": {
                "name": "Seattle-Tacoma International",
                "center_lat": 47.4489,
                "center_lon": -122.3093,
                "runways": {
                    "16L/34R": {"heading": 160.0, "length_feet": 11901.0},
                    "16C/34C": {"heading": 160.0, "length_feet": 9426.0},
                    "16R/34L": {"heading": 160.0, "length_feet": 8500.0}
                }
            }
        }

    def monitor_airport_airspace(self, airport_id, raw_adsb_feed):
        """
        Can be wired to background tracking threads to monitor ANY mapped airport 
        for sudden changes in runway traffic congestion.
        """
        if airport_id not in self.airport_db:
            return None
        apt = self.airport_db[airport_id]
        
        return self.geo_engine.analyze_adsb_traffic_density(
            adsb_raw_data=raw_adsb_feed,
            center_lat=apt["center_lat"],
            center_lon=apt["center_lon"]
        )

    def _load_mock_db(self):
        return {"KSEA": {"center_lat": 47.4489, "center_lon": -122.3093, "runways": {"16L/34R": {"heading": 160.0, "length_feet": 11901.0}}}}

    def interactive_holding_initialization(self, airport_id, rwy_id, raw_adsb_feed):
        """
        Interactive checklist method. Queries crew specifications, showcases 
        7 clear airspace vectors, and maps flight profiles based on operational priority.
        """
        print(f"\n========================================================")
        print(f" INITIALIZING TOP-PRIORITY WAYPOINT PROFILE FOR: {airport_id}")
        print(f"========================================================")
        
        # Step 1: Scan and render the top 7 traffic-free tiers
        apt = self.airport_db[airport_id]
        clear_zones = self.geo_engine.find_top_7_traffic_free_blocks(raw_adsb_feed, apt["center_lat"], apt["center_lon"])
        
        print("\n[LIVE MONITOR] TOP 7 TRAFFIC-FREE AVAILABLE HOLDING ALTITUDES:")
        for idx, zone in enumerate(clear_zones, 1):
            print(f"  Selection {idx} -> {zone['altitude_ft']} ft | Status: {zone['status']} | Threat Vector Score: {zone['congestion_score']}")

        # Step 2: Interactive Interview Prompts (Can be wired directly to GUI or CLI input strings)
        print("\n--- REQUIRED MISSION ASSIGNMENT SPECIFICATIONS ---")
        
        # User input simulation hooks
        selected_index = int(input("Select holding altitude option (1-7): ") or "1")
        chosen_altitude = clear_zones[selected_index - 1]["altitude_ft"]
        
        plane_class = input("Enter your Aircraft Category (military/law/gov/commercial/civil): ").lower() or "military"
        is_emergency = input("Is this flight executing an Emergency Priority Override? (y/n): ").lower() == "y"
        
        print(f"\n[SUCCESS] Profile mapped. Assigned Holding Level: {chosen_altitude} feet MSL.")
        
        # Emergency priority overrides skip speed caps completely
        if is_emergency or plane_class == "military":
            max_holding_ias = "UNRESTRICTED (Tactical Priority Override Engaged)"
        else:
            max_holding_ias = f"{200 if chosen_altitude <= 6000 else 230} Knots IAS"
            
        return {
            "target_altitude": chosen_altitude,
            "aircraft_category": plane_class,
            "emergency_priority": is_emergency,
            "max_legal_speed_restriction": max_holding_ias,
            "all_evaluated_clear_zones": clear_zones
        }

    def update_holding_altitude_mid_flight(self, new_altitude, source="pilot"):
        """
        Allows the pilot or an automated ATC command parser to change 
        holding configurations dynamically at any frame during navigation.
        """
        self.active_flight_profile["assigned_holding_altitude"] = new_altitude
        if source == "atc":
            self.active_flight_profile["atc_override_active"] = True
        else:
            self.active_flight_profile["atc_override_active"] = False
            
        return f"Flight guidance loop updated. Target Altitude: {new_altitude} ft. Source: {source.upper()}"

    def process_airport_arrival(self, airport_id, rwy_id, aircraft_heading, tas_knots, wind_speed, wind_dir, mode="land", raw_adsb_feed=None, requested_altitude=None):
        """
        Upgraded arrival process. Integrates automated ADS-B traffic sorting, 
        initial altitude selection, and emergency ATC compliance layers.
        """
        apt_data = self.airport_db[airport_id]
        rwy_info = apt_data["runways"][rwy_id]
        
        # Track active target selections
        self.active_flight_profile["target_airport"] = airport_id
        self.active_flight_profile["target_runway"] = rwy_id

        # 1. Fetch live ADS-B congestion metrics if data stream is available
        traffic_report = None
        recommended_alt = 5000 # Fallback default
        
        if raw_adsb_feed:
            traffic_report = self.monitor_airport_airspace(airport_id, raw_adsb_feed)
            recommended_alt = traffic_report["recommended_clean_altitude"]

        # 2. Altitude Allocation Logic Hierarchy
        if self.active_flight_profile["atc_override_active"]:
            # Hard priority override: Tower instructions take immediate precedence
            final_altitude = self.active_flight_profile["assigned_holding_altitude"]
        elif requested_altitude is not None:
            # Secondary priority: Manual pilot entry choice
            final_altitude = requested_altitude
            self.active_flight_profile["assigned_holding_altitude"] = requested_altitude
        else:
            # Automation default: Auto-select the emptiest structural tier detected
            final_altitude = recommended_alt
            self.active_flight_profile["assigned_holding_altitude"] = recommended_alt

        # 3. Standard meteorological runway wind analysis
        runway_evaluation = self.geo_engine.determine_best_runway(
            rwy_info["heading"], rwy_info["length_feet"], wind_speed, wind_dir, apt_data["center_lat"], apt_data["center_lon"]
        )
        
        # 4. Enforce structural speed restrictions matching FAA altitude tiers
        max_ias = 200 if final_altitude <= 6000 else 230
        
        # 5. Build waypoint tracks
        pattern_type = self.geo_engine.calculate_holding_entry(aircraft_heading, runway_evaluation["heading"])
        arrival_points = self.geo_engine.generate_holding_pattern_waypoints(
            runway_evaluation["threshold"], runway_evaluation["threshold"],
            runway_evaluation["heading"], tas_knots, wind_speed, wind_dir, pattern_type
        )
        
        # Inject the dynamically determined holding altitude into every generated tracking node
        for wp in arrival_points:
            wp["target_altitude_ft"] = final_altitude

        return {
            "airport": airport_id,
            "selected_runway": rwy_id,
            "assigned_altitude": final_altitude,
            "atc_override_engaged": self.active_flight_profile["atc_override_active"],
            "recommended_clean_altitude": recommended_alt,
            "max_legal_holding_ias": max_ias,
            "traffic_density_report": traffic_report["density_map"] if traffic_report else "No ADS-B Data available",
            "generated_waypoint_stack": arrival_points
        }

    def process_airport_arrival(self, airport_id, rwy_id, aircraft_heading, tas_knots, wind_speed, wind_dir, mode="land", holding_is_standard=True):
        """
        High-level orchestration entry point called by the flight UI or telemetry loop.

        if airport_id not in self.airport_db:
            raise ValueError(f"Airport identifier '{airport_id}' not found in configuration files.")
            
        apt_data = self.airport_db[airport_id]
        if rwy_id not in apt_data["runways"]:
            raise ValueError(f"Runway '{rwy_id}' does not exist at {airport_id}.")

        rwy_info = apt_data["runways"][rwy_id]
        
        Parameters:
            airport_id (str): ICAO identifier (e.g., 'KSEA')
            rwy_id (str): User-selected runway string (e.g., '16L/34R')
            aircraft_heading (float): Current arrival track heading
            tas_knots (float): True Airspeed
            wind_speed (float): Predicted wind velocity at landing
            wind_dir (float): Meteorological wind heading source
            mode (str): Execution path selection -> "land" for touchdown zone tracking, "hold" for patterns.
            holding_is_standard (bool): True for standard right turns, False for left turns.
        """
        if airport_id not in self.airport_db:
            raise ValueError(f"Airport identifier '{airport_id}' not found in configuration files.")
            
        apt_data = self.airport_db[airport_id]
        if rwy_id not in apt_data["runways"]:
            raise ValueError(f"Runway '{rwy_id}' does not exist at {airport_id}.")

        rwy_info = apt_data["runways"][rwy_id]
        
        # 1. Dynamically evaluate the runway wind-vectors and select the safest side
        runway_evaluation = self.geo_engine.determine_best_runway(
            rwy_heading=rwy_info["heading"],
            total_length=rwy_info["length_feet"],
            wind_speed=wind_speed,
            wind_dir=wind_dir,
            center_lat=apt_data["center_lat"],
            center_lon=apt_data["center_lon"]
        )
        # 2. RUNWAY WIND SAFETY VALIDATION
        is_safe, safety_msg = self.geo_engine.validate_landing_safety(
            crosswind_kts=runway_evaluation["crosswind"],
            max_demonstrated_crosswind=max_crosswind_limit
        )
        
        # If unsafe and user requested a landing, override the mode to "hold" to preserve the aircraft
        execution_mode = mode
        safety_override_triggered = False
        
        if not is_safe and mode == "land":
            execution_mode = "hold"
            safety_override_triggered = True
                
        # 3. Extract bounding endpoints to determine the touchdown target vector
        threshold_pos = runway_evaluation["threshold"]
        opposite_pos = runway_evaluation["opposite_threshold"]
        
        # 4. Handle Mode Executions
        if execution_mode == "land":
            td_lat, td_lon = self.geo_engine.generate_touchdown_point(
                threshold_lat=threshold_pos, threshold_lon=threshold_pos,
                runway_heading=runway_evaluation["heading"],
                opposite_lat=opposite_pos, opposite_lon=opposite_pos
            )
            
            arrival_points = [
                {"label": "APPROACH_ENTRY", "lat": threshold_pos, "lon": threshold_pos},
                {"label": "TOUCHDOWN_MARK", "lat": td_lat, "lon": td_lon}
            ]
            pattern_type = "Straight-In Precision Approach"
            
        elif execution_mode == "hold":
            # Automate FAA sector entry selection
            pattern_type = self.geo_engine.calculate_holding_entry(
                aircraft_heading=aircraft_heading,
                inbound_course=runway_evaluation["heading"],
                is_standard=holding_is_standard
            )
            
            # Build coordinate array blocks for the hold sequence over the threshold
            arrival_points = self.geo_engine.generate_holding_pattern_waypoints(
                fix_lat=threshold_pos, fix_lon=threshold_pos,
                inbound_course=runway_evaluation["heading"],
                tas_knots=tas_knots, wind_speed=wind_speed, wind_dir=wind_dir,
                entry_type=pattern_type, is_standard=holding_is_standard
            )

        # 5. Apply distance kinematics to resolve arrival projections
        target_dest = arrival_points[-1]
        ete_minutes = self.geo_engine.estimate_arrival_time(
            current_lat=apt_data["center_lat"] + 0.1, 
            current_lon=apt_data["center_lon"] - 0.1,
            target_lat=target_dest["lat"], target_lon=target_dest["lon"],
            tas_knots=tas_knots, wind_speed=wind_speed, wind_dir=wind_dir
        )
        
        # Comprehensive telemetry pack with safety status flags
        return {
            "airport": airport_id,
            "selected_runway_side": runway_evaluation["side"],
            "landing_magnetic_heading": runway_evaluation["heading"],
            "resolved_pattern_type": pattern_type,
            "calculated_headwind_knots": runway_evaluation["headwind"],
            "calculated_crosswind_knots": runway_evaluation["crosswind"],
            "estimated_time_enroute_minutes": ete_minutes,
            "generated_waypoint_stack": arrival_points,
            "safety_status": {
                "landing_allowed": is_safe,
                "safety_override_triggered": safety_override_triggered,
                "message": safety_msg
            }
# Sample testing implementation execution
if __name__ == "__main__":
    root_manager = RootWaypointManager()
    
    # Simulate a user requesting a holding pattern arrival configuration
    telemetry_output = root_manager.process_airport_arrival(
        airport_id="KSEA",
        rwy_id="16L/34R",
        aircraft_heading=210.0, # Approach track heading
        tas_knots=150.0,
        wind_speed=22.0,
        wind_dir=340.0,         # Strong wind out of the NNW
        mode="hold"             # Options: "hold" or "land"
    )
    
    print(json.dumps(telemetry_output, indent=4))

class WaypointManager:
    @njit(fastmath=True)
    def generate_circular_pattern(self, center_lat, center_lon, radius_nm, waypoint_count=36):
        """ Generates a high-fidelity circular orbit (The Big Circle) natively. """
        
        """ GUARD 1: Validate physical radius """
        if radius_nm <= 0.0:
            return []

        """ GUARD 2: Prevent zero-division on waypoint geometry """
        if waypoint_count <= 0:
            waypoint_count = 36

        path = []
        
        """ HAPPY PATH: Calculate angles seamlessly using array spaces """
        theta = xp.linspace(0, 2 * math.pi, waypoint_count, endpoint=False)
        
        for angle in theta:
            lat_offset = (radius_nm / 60.0) * math.cos(angle)
            lon_offset = (radius_nm / 60.0) * math.sin(angle)
            
            path.append({
                "lat": center_lat + lat_offset,
                "lon": center_lon + lon_offset,
                "alt": getattr(self, 'current_flight_level', 0.0),
                "type": "HOLDING_POINT"
            })
            
        return path


    @njit(fastmath=True)
    def calculate_environmental_drift(self, v_current, v_wind, c_ice_penalty):
        """ Calculates velocity degradation due to ice accumulation and wind shear. """
        
        """ GUARD: Prevent inverted physics from bad ice telemetry """
        if c_ice_penalty < 0.0 or c_ice_penalty > 1.0:
            c_ice_penalty = 0.0
            
        """ V_net = V_current + V_wind - (V_current * C_ice) """
        v_net = []
        for i in range(3):
            net_axis = v_current[i] + v_wind[i] - (v_current[i] * c_ice_penalty)
            v_net.append(net_axis)
            
        return v_net
    
    @njit(fastmath=True)
    def __init__(self, config_path="config.json", catalog_path="src/catalog-3.23.dat"):
        """ Load the Firewall and the Space Catalog """
        self.specs = self._load_and_validate_config(config_path)
        
        """ GUARD: Config corrupted, inject emergency defaults """
        if not self.specs:
            print("WARNING: Config rejected by Firewall. Using synthetic physics.")
            self.specs = VehicleSpecs(
                vehicle_mass_kg=50000.0,
                wing_area_m2=100.0,
                cd0=0.02,
                induced_drag_k=0.05,
                nose_radius_m=1.5,
                max_thrust_n=250000.0
            )

        self.MAX_THRUST_N = float(self.specs.max_thrust_n)
        self.DISTANCE_THRESHOLD_M = 15.000000000000000
        self.V1_SPEED_KTS = 135.000000000000000
        self.VR_SPEED_KTS = 145.000000000000000
        
        """ FSM Tracking """
        self.current_waypoint = "WP1"
        self.fsm_state = "TAXIING_MODE"
        self.s_turn_enabled = False
        self.active_space_target = None
        
        """ EKF Tracking Memory """
        self.P_matrix = xp.eye(6)
        self.Q_matrix = xp.eye(6) * 0.01

        """ External Engines """
        self.entry_controller = EntryController()
        self.dso_catalog = self._load_space_catalog(catalog_path)

    @njit(fastmath=True)
    def _load_and_validate_config(self, config_path):
        """ Else-less JSON payload loader and strict data validator. """
        if not os.path.exists(config_path):
            return None
            
        try:
            with open(config_path, 'r') as file:
                payload = json.load(file)
            return VehicleSpecs(**payload)
        except (json.JSONDecodeError, PermissionError, ValidationError):
            return None

    @njit(fastmath=True)
    def _load_space_catalog(self, catalog_path):
        """ Else-less DSO parser for Universal Mapping. """
        if not os.path.exists(catalog_path): return {}
        try:
            with open(catalog_path, 'rb') as file:
                return {"status": "LOADED"}
        except Exception:
            return {}

    @njit(fastmath=True)
    def evaluate_ground_state(self, strut_pressures_psi, aerodynamic_lift_n, aircraft_weight_n):
        """ Weight-on-Wheels (WoW) logic matrix. """
        if aerodynamic_lift_n >= aircraft_weight_n: return 0
        if sum(strut_pressures_psi) < 1000.0: return 0
        return 1

    @njit(fastmath=True)
    def determine_fsm_transition(self, ground_state, ground_speed_kts, thrust_level):
        """ Translates physical state into explicit FSM Modes. """
        if ground_state == 0:
            self.fsm_state = "AERIAL_FLIGHT_MODE"
            return self.fsm_state

        bridge_state = telemetry_link.get_global_state("authority", "system_state")
        if bridge_state == "ELSE":
            self.fsm_state = "EMERGENCY_ABORT_MODE"
            return self.fsm_state

        if ground_speed_kts >= 50.0 and thrust_level > (self.MAX_THRUST_N * 0.8):
            self.fsm_state = "TAKEOFF_RUN_MODE"
            return self.fsm_state
            
        self.fsm_state = "TAXIING_MODE"
        return self.fsm_state

    @njit(fastmath=True)
    def check_takeoff_sequence(self, current_pos, wp1_pos, wp2_pos, wp3_pos, velocity_kts, thrust_level):
        """ Else-less Tactical Takeoff FSM anchored to 3 physical waypoints. """
        if self.current_waypoint not in ["WP1", "WP2", "WP3"]:
            return "HOLD_POSITION"

        if self.current_waypoint == "WP1":
            if thrust_level < self.MAX_THRUST_N: return "HOLD_BRAKES_SPOOL_ENGINES"
            self.current_waypoint = "WP2"
            return "RELEASE_BRAKES"

        if self.current_waypoint == "WP2":
            d_wp2 = calculate_spatial_distance(
                current_pos['lat'], current_pos['lon'], current_pos['alt'],
                wp2_pos['lat'], wp2_pos['lon'], wp2_pos['alt']
            )
            if d_wp2 >= self.DISTANCE_THRESHOLD_M: return "CONTINUE_ACCELERATION"
            if velocity_kts < self.V1_SPEED_KTS: return "ABORT_TAKEOFF"
            
            self.current_waypoint = "WP3"
            return "CONTINUE_ACCELERATION"

        d_wp3 = calculate_spatial_distance(
            current_pos['lat'], current_pos['lon'], current_pos['alt'],
            wp3_pos['lat'], wp3_pos['lon'], wp3_pos['alt']
        )
        if d_wp3 >= self.DISTANCE_THRESHOLD_M and velocity_kts < self.VR_SPEED_KTS:
            return "CONTINUE_ACCELERATION"

        return "EXECUTE_TACTICAL_ROTATION"

    @njit(fastmath=True)
    def process_ground_ekf_cycle(self, x_hat, u_vector, dt):
        """ Updates the ground tracking Extended Kalman Filter matrix. """
        x_new, P_new = ekf_prediction_step(xp.array(x_hat), xp.array(u_vector), self.P_matrix, self.Q_matrix, float(dt))
        self.P_matrix = P_new
        
        if HAS_GPU: return xp.round(x_new, 15).get().tolist()
        return xp.round(x_new, 15).tolist()

    @njit(fastmath=True)
    def set_s_turn_mode(self, active: bool):
        self.s_turn_enabled = active
        telemetry_link.update_global_state("navigation", "s_turn_mode", self.s_turn_enabled)
        return self.s_turn_enabled

    @njit(fastmath=True)
    def _inject_s_turn_maneuver(self, intercept_dict):
        intercept_dict['maneuver'] = "S-TURN_ENERGY_BLEED"
        intercept_dict['bank_cmd_deg'] = 45.000000000000000
        return intercept_dict

    @njit(fastmath=True)
    def export_planned_trajectory(self, current_pos, current_vel, time_horizon_s=60.0, dt=1.0):
        if not self.active_space_target: return []

        trajectory = []
        steps = int(time_horizon_s / dt)
        
        for t in range(steps):
            future_x = current_pos[0] + (current_vel[0] * t * dt)
            future_y = current_pos[1] + (current_vel[1] * t * dt)
            future_z = current_pos[2] + (current_vel[2] * t * dt)
            
            trajectory.append({
                "time_offset_sec": round(float(t * dt), 15),
                "predicted_x": round(float(future_x), 15),
                "predicted_y": round(float(future_y), 15),
                "predicted_z": round(float(future_z), 15)
            })
            
        return trajectory

    @njit(fastmath=True)
    def calculate_universal_intercept(self, ship_pos, ship_vel, target_alt_m=0.0):
        """ Standard 3D Intercept Engine. """
        if not self.active_space_target: return None
            
        target_pos = self.active_space_target.get("position_vec", [0.0, 0.0, 0.0])
        target_radius = self.active_space_target.get("radius", 0.0) + target_alt_m
        
        dist, tti = compute_intercept_metrics(
            float(ship_pos[0]), float(ship_pos[1]), float(ship_pos[2]),
            float(ship_vel[0]), float(ship_vel[1]), float(ship_vel[2]),
            float(target_pos[0]), float(target_pos[1]), float(target_pos[2]),
            float(target_radius)
        )
        
        return {
            "status": "TRACKING_ACTIVE",
            "distance_m": round(float(dist), 15),
            "time_to_intercept_sec": round(float(tti), 15)
        }

    @njit(fastmath=True)
    def calculate_tactical_approach(self, ship_pos, ship_vel, altitude_m):
        """ Absolute Navigation Gatekeeper. Triggers Atmospheric Entry if descending to Earth. """
        
        current_frame = telemetry_link.get_global_state("navigation", "planetary_reference_frame")
        
        """ GUARD 1: If frame is NOT Earth, Terrestrial formulas are physically invalid. """
        if current_frame != "Earth":
            return self.calculate_universal_intercept(ship_pos, ship_vel, target_alt_m=0.0)

        """ GUARD 2: High Altitude Entry Detection (Above 85,000m) """
        if altitude_m > 85000.0:
            """ Route the telemetry directly to the Entry Controller for heating calculations """
            telemetry_override = {'alt_m': [altitude_m], 'vel_mps': [math.sqrt(sum([v**2 for v in ship_vel]))]}
            entry_data = self.entry_controller.run_entry_sequence(telemetry_override)
            return {"maneuver": "ATMOSPHERIC_ENTRY", "heating_data": entry_data}

        """ HAPPY PATH: Terrestrial Standard Approach """
        intercept = self.calculate_universal_intercept(ship_pos, ship_vel, target_alt_m=0.0)
        if not intercept: return None

        """ GUARD 3: High Energy Profile -> Inject Tactical S-Turn """
        if self.s_turn_enabled:
            return self._inject_s_turn_maneuver(intercept)

        """ Default: Direct Tactical Descent """
        intercept['maneuver'] = "DIRECT_TACTICAL_DESCENT"
        intercept['bank_cmd_deg'] = 0.000000000000000
        return intercept
