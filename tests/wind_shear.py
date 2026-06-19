if __name__ == "__main__":
    root_mgr = RootWaypointManager()
    
    # Heavy aircraft tracking a westbound holding arc at 180 Knots
    mock_ac = {"class": "heavy", "lat": 47.448, "lon": -122.309, "alt_ft": 6000.0, "tas_kts": 180.0, "hdg_deg": 270.0}
    
    # Frame 0: Baseline state initialization pass
    wind_frame_0 = {"direction_deg": 270.0, "speed_kts": 15.0}
    _ = root_mgr.process_dynamic_pattern_shear(mock_ac, wind_frame_0, dt=1.0)
    
    # Frame 1: Dynamic Microburst Intercept Encounter (Severe 12-knot shear spike across 1 second)
    wind_frame_1 = {"direction_deg": 285.0, "speed_kts": 27.0}
    
    print("=================================================================")
    print("      EXECUTING LIVE MICROBURST/WIND SHEAR TRACKING MATRIX       ")
    print("=================================================================")
    print(f"Wind Velocity Frame 0: {wind_frame_0['speed_kts']} kts @ {wind_frame_0['direction_deg']}°")
    print(f"Wind Velocity Frame 1: {wind_frame_1['speed_kts']} kts @ {wind_frame_1['direction_deg']}° (Severe Delta Encounter)")
    
    shear_report = root_mgr.process_dynamic_pattern_shear(
        ac_telemetry=mock_ac,
        live_wind_profile=wind_frame_1,
        dt=1.0, # One second update interval
        weight_category="heavy"
    )
    
    print("\n---------------- INTEGRATED CONTROL BUS SAFETY RECOVERY ---------")
    print(f"Measured Shear Intensity  : {shear_report['measured_shear_gradient_kts_sec']:.2f} Knots/Second")
    print(f"Commanded Flight Roll     : {shear_report['commanded_bank_angle_degrees']:.1f}° Corrective Bank Target")
    print(f"Calculated Spatial Radius : {shear_report['computed_safe_turn_radius_meters']:.1f} Meters")
    print(f"Airspace Emergency Status : {shear_report['structural_limit_override_engaged']}")
    
    # Render the new data packet structure
    mock_jit_out = np.array([-1500.0, 274.5, 22.1, 8500.0, 4200.0, 32.5], dtype=np.float64) # Simulated base bus outputs
    binary_bus = encode_to_1553b_avionics_bus(mock_jit_out, shear_report)
    print(f"Encoded 1553B Hex Payload : {binary_bus.hex().upper()}")
