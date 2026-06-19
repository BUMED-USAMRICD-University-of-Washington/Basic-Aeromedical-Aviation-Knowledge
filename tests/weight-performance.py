if __name__ == "__main__":
    root_mgr = RootWaypointManager()
    
    # Flight scenario inputs
    aircraft_type = "heavy"
    current_ias_kts = 210.0
    current_altitude_ft = 12000.0
    
    # The legally verified westbound flight level returned by your previous routine
    target_faa_holding_level = 6000.0  
    
    print("=================================================================")
    print("     EXECUTING NUMBA JIT ACCELERATED VERTICAL INTERFACE LOOP    ")
    print("=================================================================")
    print(f"Current Telemetry State : {current_altitude_ft} ft @ {current_ias_kts} kts")
    print(f"Target FAA Holding Level: {target_faa_holding_level} ft")
    print(f"Aircraft Classification : {aircraft_type.upper()}")
    
    # Execute the JIT boundary loop transition
    commanded_vs, vertical_error = root_mgr.pipe_holding_altitude_to_jit_loop(
        current_altitude=current_altitude_ft,
        current_speed=current_ias_kts,
        selected_faa_level=target_faa_holding_level,
        weight_category=aircraft_type
    )
    
    print("\n---------------------- HARDWARE GUIDANCE OUTPUT -----------------")
    print(f"Altitude Error Calculation : {vertical_error:.1f} feet")
    print(f"Commanded Autopilot Target : {commanded_vs:.1f} Feet Per Minute (FPM)")
    
    if commanded_vs < 0:
        print("[STATUS]: Executing structural glideslope-limited energy descent profile.")
    elif commanded_vs > 0:
        print("[STATUS]: Executing optimal airframe performance power climb profile.")
    else:
        print("[STATUS]: Level flight achieved. Holding assigned FAA vertical separation block.")
