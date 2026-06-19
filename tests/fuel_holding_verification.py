if __name__ == "__main__":
    root_mgr = RootWaypointManager()
    
    # Telemetry data array input parameters
    aircraft_class = "medium"
    onboard_fuel_lbs = 6500.0
    diversion_route_fuel_lbs = 1800.0  # Fuel required to exit hold and reach alternate port
    assigned_level_ft = 8000.0
    
    print("=================================================================")
    print("       LIVE FUEL EFFICIENCY & ENDURANCE MONITOR TEST RUN         ")
    print("=================================================================")
    print(f"Initial Aircraft Fuel State: {onboard_fuel_lbs} lbs")
    print(f"Target Assigned Flight Level: {assigned_level_ft} feet")
    
    # CASE A: Level, standard-rate stabilization turn (Safe, low bank angle)
    print("\n[SCENARIO A]: Stable Straight-In Holding Track (15° Low-Bank Cornering)")
    report_a = root_mgr.monitor_holding_efficiency(
        current_fuel_lbs=onboard_fuel_lbs,
        aircraft_type=aircraft_class,
        altitude_ft=assigned_level_ft,
        bank_angle_deg=15.0,
        destination_diversion_fuel_lbs=diversion_route_fuel_lbs
    )
    print(f" -> Real-time Fuel Flow : {report_a['calculated_fuel_flow_pph']} PPH")
    print(f" -> Absolute Bingo Fuel : {report_a['total_bingo_fuel_threshold_lbs']} lbs")
    print(f" -> REMAINING HOLD TIME : {report_a['remaining_hold_endurance_minutes']} minutes")
    print(f" -> Safety Assessment   : {report_a['safety_assessment']}")
    
    # CASE B: Steep, sudden correction turn to handle severe wind drift
    print("\n[SCENARIO B]: High-Bank Wind Drift Correction Turn (45° High-Bank)")
    report_b = root_mgr.monitor_holding_efficiency(
        current_fuel_lbs=onboard_fuel_lbs,
        aircraft_type=aircraft_class,
        altitude_ft=assigned_level_ft,
        bank_angle_deg=45.0,
        destination_diversion_fuel_lbs=diversion_route_fuel_lbs
    )
    print(f" -> Real-time Fuel Flow : {report_b['calculated_fuel_flow_pph']} PPH (Burn rate spike!)")
    print(f" -> Absolute Bingo Fuel : {report_b['total_bingo_fuel_threshold_lbs']} lbs")
    print(f" -> REMAINING HOLD TIME : {report_b['remaining_hold_endurance_minutes']} minutes (Time drops)")
