import numpy as np

class WaypointManager:
    def __init__(self):
        # Earth parameters for coordinate conversion (meters per degree latitude)
        self.LAT_METERS = 111132.95
        
        # Priority Coefficients dictionary mapped for structural spacing math
        self.PRIORITY_COEFFS = {
            "military":  {"omega": 0.20, "psi": 0.00},
            "law":       {"omega": 0.25, "psi": 0.00},
            "gov":       {"omega": 0.40, "psi": 0.50},
            "commercial":{"omega": 0.60, "psi": 1.00},
            "freight":   {"omega": 0.80, "psi": 1.00},
            "us_mail":   {"omega": 1.00, "psi": 1.00},
            "civil":     {"omega": 1.50, "psi": 2.00}
        }
    def analyze_adsb_traffic_density(self, adsb_raw_data, center_lat, center_lon, radius_nm=15.0):
        """
        Parses live ADS-B state vectors within a specific radius of the airport.
        Groups aircraft into 1,000-ft vertical holding blocks to find the least congested level.
        """
        # Initialize standard aviation holding blocks (e.g., 3,000 ft up to 12,000 ft)
        altitude_blocks = {alt: 0 for alt in range(3000, 13000, 1000)}
        
        # Distance scaling approximation
        lon_meters = 111412.84 * np.cos(np.radians(center_lat))
        radius_meters = radius_nm * 1852.0  # Nautical miles to meters
        
        for aircraft in adsb_raw_data.get("ac", []):
            ac_lat = aircraft.get("lat")
            ac_lon = aircraft.get("lon")
            ac_alt = aircraft.get("alt_baro") # Barometric altitude in feet
            
            if ac_lat is None or ac_lon is None or ac_alt is None:
                continue
                
            # Verify if aircraft is within the airport's terminal holding airspace
            d_lat = (ac_lat - center_lat) * self.LAT_METERS
            d_lon = (ac_lon - center_lon) * lon_meters
            distance = np.sqrt(d_lat**2 + d_lon**2)
            
            if distance <= radius_meters:
                # Round to the nearest 1,000-foot holding assignment block
                rounded_alt = int(round(ac_alt / 1000.0) * 1000)
                if rounded_alt in altitude_blocks:
                    altitude_blocks[rounded_alt] += 1
                    
        # Identify the block with the minimum number of target aircraft tracks
        best_altitude = min(altitude_blocks, key=altitude_blocks.get)
        
        return {
            "density_map": altitude_blocks,
            "recommended_clean_altitude": best_altitude,
            "traffic_at_recommendation": altitude_blocks[best_altitude]
        }
    
    def find_top_7_traffic_free_blocks(self, adsb_raw_data, center_lat, center_lon, radius_nm=15.0):
        """
        Scans live traffic and tracks exactly which 1,000-ft altitude slots 
        from 2,000 to 15,000 feet contain zero or the fewest aircraft.
        Returns up to 7 options sorted by safety/clarity score.
        """
        # Define available holding bands
        valid_tiers = range(2000, 16000, 1000)
        altitude_scores = {alt: 0.0 for alt in valid_tiers}
        aircraft_counts = {alt: 0 for alt in valid_tiers}
        
        lon_meters = 111412.84 * np.cos(np.radians(center_lat))
        
        for aircraft in adsb_raw_data.get("ac", []):
            ac_lat = aircraft.get("lat")
            ac_lon = aircraft.get("lon")
            ac_alt = aircraft.get("alt_baro")
            # Map intruder to operational category (defaults to civil GA if missing)
            ac_cat = aircraft.get("category", "civil").lower()
            
            if ac_lat is None or ac_lon is None or ac_alt is None:
                continue
                
            # Distance vectors
            d_lat = (ac_lat - center_lat) * self.LAT_METERS
            d_lon = (ac_lon - center_lon) * lon_meters
            dist_nm = np.sqrt(d_lat**2 + d_lon**2) / 1852.0 # convert to NM
            
            if dist_nm <= radius_nm:
                # Apply priority spacing modifier calculation
                coeffs = self.PRIORITY_COEFFS.get(ac_cat, {"omega": 1.50, "psi": 2.00})
                effective_h_limit = 3.0 * (1.0 + coeffs["omega"])
                
                # Check which holding tiers this intruder corrupts vertically
                for tier in valid_tiers:
                    v_diff = abs(ac_alt - tier)
                    effective_v_limit = 1000 * (1.0 + coeffs["psi"])
                    
                    # If aircraft breaches safety footprint, penalize the score of that tier
                    if dist_nm <= effective_h_limit and v_diff <= effective_v_limit:
                        aircraft_counts[tier] += 1
                        # Closer targets with high-priority penalties spike the score (lower is clearer)
                        altitude_scores[tier] += (10.0 / (dist_nm + 0.1)) * (1.0 + coeffs["omega"])

        # Sort tiers based on density/threat scores, then alphabetically by altitude
        sorted_tiers = sorted(valid_tiers, key=lambda x: (altitude_scores[x], aircraft_counts[x], x))
        
        # Package the top 7 cleanest altitude configurations
        top_7_options = []
        for alt in sorted_tiers[:7]:
            status = "COMPLETELY OPEN" if aircraft_counts[alt] == 0 else f"CONGESTED ({aircraft_counts[alt]} targets nearby)"
            top_7_options.append({
                "altitude_ft": alt,
                "congestion_score": round(altitude_scores[alt], 2),
                "aircraft_count": aircraft_counts[alt],
                "status": status
            })
            
        return top_7_options
        
    def get_runway_ends(self, center_lat, center_lon, true_heading, total_length_feet):
        """
        Calculates the geographic coordinates of both thresholds of a runway.
        All calculations convert standard aviation feet metrics to SI meters.
        """
        length_meters = total_length_feet * 0.3048
        half_len = length_meters / 2.0
        
        # Longitude scaling factor based on latitude
        lon_meters = 111412.84 * np.cos(np.radians(center_lat))
        
        heading_rad = np.radians(true_heading)
        delta_lat = half_len * np.cos(heading_rad)
        delta_lon = half_len * np.sin(heading_rad)
        
        # Threshold A (The direction the runway points from center)
        lat_a = center_lat + (delta_lat / self.LAT_METERS)
        lon_a = center_lon + (delta_lon / lon_meters)
        
        # Threshold B (Opposite end)
        lat_b = center_lat - (delta_lat / self.LAT_METERS)
        lon_b = center_lon - (delta_lon / lon_meters)
        
        return (lat_a, lon_a), (lat_b, lon_b)
        
    def validate_landing_safety(self, crosswind_kts, max_demonstrated_crosswind=15.0):
        """
        Validates whether the landing can be safely executed based on aircraft limits.
        Returns a boolean status and an error message if limits are breached.
        """
        if abs(crosswind_kts) > max_demonstrated_crosswind:
            return False, f"CRITICAL: Crosswind component ({crosswind_kts:.1f} kts) exceeds maximum demonstrated limit ({max_demonstrated_crosswind:.1f} kts)."
        return True, "Weather within safe operating margins."

    def determine_best_runway(self, rwy_heading, total_length, wind_speed, wind_dir, center_lat, center_lon):
        """
        Evaluates both sides of a runway to determine the safest landing vector.
        Recommends the specific runway side maximizing headwind and minimizing crosswinds.
        """
        side_1_hdg = rwy_heading
        side_2_hdg = (rwy_heading + 180) % 360
        
        pos_a, pos_b = self.get_runway_ends(center_lat, center_lon, rwy_heading, total_length)
        
        # Vector evaluation helper
        def eval_side(heading):
            theta = np.radians(abs(wind_dir - heading))
            headwind = wind_speed * np.cos(theta)
            crosswind = wind_speed * np.sin(theta)
            return headwind, crosswind

        hw1, xw1 = eval_side(side_1_hdg)
        hw2, xw2 = eval_side(side_2_hdg)
        
        # Optimization logic selecting highest headwind vector
        if hw1 >= hw2:
            return {"side": "Primary (Threshold A)", "heading": side_1_hdg, "threshold": pos_b, "touchdown": pos_b, "headwind": hw1, "crosswind": xw1, "opposite_threshold": pos_a}
        else:
            return {"side": "Reciprocal (Threshold B)", "heading": side_2_hdg, "threshold": pos_a, "touchdown": pos_a, "headwind": hw2, "crosswind": xw2, "opposite_threshold": pos_b}

    def generate_touchdown_point(self, threshold_lat, threshold_lon, runway_heading, opposite_lat, opposite_lon):
        """
        Offsets the arrival target exactly 1,000 feet (304.8 meters) past the 
        physical threshold down the centerline to hit the painted touchdown zone markings.
        """
        lon_meters = 111412.84 * np.cos(np.radians(threshold_lat))
        
        # Direct unit vector toward the opposite threshold
        v_lat = (opposite_lat - threshold_lat) * self.LAT_METERS
        v_lon = (opposite_lon - threshold_lon) * lon_meters
        v_mag = np.sqrt(v_lat**2 + v_lon**2)
        
        u_lat = v_lat / v_mag
        u_lon = v_lon / v_mag
        
        # 1,000 feet touchdown marker offset
        offset_m = 1000 * 0.3048
        
        td_lat = threshold_lat + ((u_lat * offset_m) / self.LAT_METERS)
        td_lon = threshold_lon + ((u_lon * offset_m) / lon_meters)
        
        return td_lat, td_lon

    def calculate_holding_entry(self, aircraft_heading, inbound_course, is_standard=True):
        """
        Automates FAA holding sector allocation.
        Calculates the entry profile based on intercept angles.
        """
        delta_theta = (aircraft_heading - inbound_course) % 360
        
        if is_standard: # Right turns
            if 110 <= delta_theta < 220:
                return "Parallel"
            elif 220 <= delta_theta < 290:
                return "Teardrop"
            else:
                return "Direct"
        else: # Left turns
            if 70 <= delta_theta < 140:
                return "Teardrop"
            elif 140 <= delta_theta < 250:
                return "Parallel"
            else:
                return "Direct"

    def generate_holding_pattern_waypoints(self, fix_lat, fix_lon, inbound_course, tas_knots, wind_speed, wind_dir, entry_type, is_standard=True):
        """
        Builds a 4-point geometric coordinate stack mapped out in space for the hold.
        Applies a 3x outbound Wind Correction Angle (WCA) multiplier to preserve airspace limits.
        """
        lon_meters = 111412.84 * np.cos(np.radians(fix_lat))
        
        # Resolve basic wind vector components
        wind_rad = np.radians(wind_dir)
        w_en = wind_speed * np.sin(wind_rad) * 0.51444  # knots to m/s
        w_n = wind_speed * np.cos(wind_rad) * 0.51444
        
        # Calculate nominal flight metrics
        tas_ms = tas_knots * 0.51444
        omega = np.radians(3.0)  # Standard rate 3 deg/sec
        bank_angle = np.degrees(np.arctan((tas_ms * omega) / 9.81))
        turn_radius = (tas_ms**2) / (9.81 * np.tan(np.radians(bank_angle)))
        
        # Ground speed tracking on baseline course
        ib_rad = np.radians(inbound_course)
        ob_rad = np.radians((inbound_course + 180) % 360)
        
        # Inbound Wind Correction Angle
        v_cross_ib = wind_speed * np.sin(np.radians(wind_dir - inbound_course))
        wca_ib = np.degrees(np.arcsin(v_cross_ib / tas_knots)) if tas_knots > v_cross_ib else 0
        
        # Triple-WCA allocation rule for outbound drift containment
        wca_ob = -3.0 * wca_ib
        ob_hdg = ((inbound_course + 180) + wca_ob) % 360
        
        # Outbound Groundspeed calculation
        v_head_ob = wind_speed * np.cos(np.radians(wind_dir - ob_hdg))
        gs_ob_ms = (tas_knots - v_head_ob) * 0.51444
        leg_length_m = gs_ob_ms * 60.0  # 1-minute standard leg length
        
        waypoints = []
        
        # Coordinate tracking vectors
        ob_rad_corr = np.radians(ob_hdg)
        dx_ob = leg_length_m * np.sin(ob_rad_corr)
        dy_ob = leg_length_m * np.cos(ob_rad_corr)
        
        # Offsets for width separation (perpendicular to the inbound course)
        perp_rad = np.radians((inbound_course + (90 if is_standard else -90)) % 360)
        dx_perp = (2 * turn_radius) * np.sin(perp_rad)
        dy_perp = (2 * turn_radius) * np.cos(perp_rad)

        if entry_type == "Direct":
            # Fix Point Arrival
            waypoints.append({"label": "HOLD_FIX", "lat": fix_lat, "lon": fix_lon})
            # Outbound turn exit
            lat1 = fix_lat + (dy_perp / self.LAT_METERS)
            lon1 = fix_lon + (dx_perp / lon_meters)
            waypoints.append({"label": "OUTBOUND_START", "lat": lat1, "lon": lon1})
            # Outbound leg end
            lat2 = lat1 + (dy_ob / self.LAT_METERS)
            lon2 = lon1 + (dx_ob / lon_meters)
            waypoints.append({"label": "INBOUND_TURN_FIX", "lat": lat2, "lon": lon2})
            
        elif entry_type == "Teardrop":
            # Direct to fix
            waypoints.append({"label": "HOLD_FIX", "lat": fix_lat, "lon": fix_lon})
            # Fly 30 degrees offset inside protected airspace
            td_offset = -30 if is_standard else 30
            td_hdg = np.radians((inbound_course + 180 + td_offset) % 360)
            lat1 = fix_lat + ((tas_ms * 60.0 * np.cos(td_hdg)) / self.LAT_METERS)
            lon1 = fix_lon + ((tas_ms * 60.0 * np.sin(td_hdg)) / lon_meters)
            waypoints.append({"label": "TEARDROP_TURN_POINT", "lat": lat1, "lon": lon1})
            
        elif entry_type == "Parallel":
            # Direct to fix
            waypoints.append({"label": "HOLD_FIX", "lat": fix_lat, "lon": fix_lon})
            # Reverse along non-protected path
            lat1 = fix_lat + ((gs_ob_ms * 60.0 * np.cos(ob_rad)) / self.LAT_METERS)
            lon1 = fix_lon + ((gs_ob_ms * 60.0 * np.sin(ob_rad)) / lon_meters)
            waypoints.append({"label": "PARALLEL_LEG_END", "lat": lat1, "lon": lon1})
            
        return waypoints

    def estimate_arrival_time(self, current_lat, current_lon, target_lat, target_lon, tas_knots, wind_speed, wind_dir):
        """
        Calculates distance over ground and applies wind vectors to yield 
        estimated flight times (ETE) directly to the touchdown zone.
        """
        lon_meters = 111412.84 * np.cos(np.radians(current_lat))
        d_lat = (target_lat - current_lat) * self.LAT_METERS
        d_lon = (target_lon - current_lon) * lon_meters
        distance_m = np.sqrt(d_lat**2 + d_lon**2)
        
        # Calculate true flight heading to point
        course_rad = np.arctan2(d_lon, d_lat)
        course_deg = np.degrees(course_rad) % 360
        
        # Incorporate wind penalty along track
        tas_ms = tas_knots * 0.51444
        v_head = wind_speed * np.cos(np.radians(wind_dir - course_deg)) * 0.51444
        gs_ms = tas_ms - v_head
        
        if gs_ms <= 0:
            return float('inf') # Groundspeed zero boundary safety
            
        ete_seconds = distance_m / gs_ms
        return ete_seconds / 60.0 # Returns minutes
