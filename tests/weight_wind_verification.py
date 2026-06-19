if __name__ == "__main__":
    root_mgr = RootWaypointManager()
    
    # Real-time state of the arriving airframe
    mock_aircraft_telemetry = {
        "lat": 47.5000, 
        "lon": -122.3500, 
        "altitude_ft": 9500.0,  # Currently high above target
        "tas_knots": 160.0, 
        "heading_deg": 120.0
    }
    
    # Active holding target waypoint coordinate block
    mock_active_target_wp = {
        "label": "HOLD_FIX_34L",
        "lat": 47.4746, 
        "lon": -122.2965
    }
    
    # Legally validated flight level derived by our prior semi-circular routines
    assigned_faa_level = 6000.0 
    
    # Storm parameters
    mock_wind_profile = {
        "direction_deg": 270.0, # Wind blasting from the direct West
        "speed_kts": 30.0
    }
    
    print("=================================================================")
    print("      EXECUTING UNIFIED 3D JIT MULTI-AXIS AUTOMATION CYCLE       ")
    print("=================================================================")
    
    # Fire calculation matrix
    guidance_pack = root_mgr.calculate_unified_3d_guidance(
        aircraft_telemetry=mock_aircraft_telemetry,
        target_wp_dict=mock_active_target_wp,
        target_altitude=assigned_faa_level,
        wind_profile=mock_wind_profile,
        weight_category="heavy"
    )
    
    print("\n---------------- INTEGRATED AUTOPILOT COMMAND BUS --------------")
    print(f"VERTICAL CONTROL   -> Commanded Rate: {guidance_pack['commanded_vertical_speed_fpm']:.1f} FPM")
    print(f"HORIZONTAL CONTROL -> Target Crab Heading: {guidance_pack['commanded_autopilot_heading_deg']:.2f}°")
    print(f"WIND MONITOR       -> Resolved Crosswind Component: {guidance_pack['resolved_crosswind_component_kts']:.1f} Kts")
