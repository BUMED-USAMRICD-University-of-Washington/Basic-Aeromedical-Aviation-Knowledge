if __name__ == "__main__":
    root_manager = RootWaypointManager()
    
    # Mocking real-world raw ADS-B Exchange JSON payload returning aircraft targets near Seattle
    mock_adsb_exchange_feed = {
        "ac": [
            {"id": "A123", "lat": 47.45, "lon": -122.31, "alt_baro": 4100}, # Aircraft in 4000ft tier
            {"id": "B456", "lat": 47.44, "lon": -122.30, "alt_baro": 3950}, # Aircraft in 4000ft tier
            {"id": "C789", "lat": 47.46, "lon": -122.32, "alt_baro": 6050}, # Aircraft in 6000ft tier
            {"id": "D101", "lat": 47.43, "lon": -122.29, "alt_baro": 5000}, # Aircraft in 5000ft tier
            # Notice 7,000 feet remains completely clear of target returns
        ]
    }
    
    print("--- STEP 1: INITIAL ARRIVAL (AUTOMATIC LEAST-TRAFFIC LEVEL SELECTION) ---")
    telemetry = root_manager.process_airport_arrival(
        airport_id="KSEA", rwy_id="16L/34R", aircraft_heading=210.0,
        tas_knots=140.0, wind_speed=10.0, wind_dir=340.0,
        mode="hold", raw_adsb_feed=mock_adsb_exchange_feed
    )
    print(f"Airspace Scan Result - Emptiest Recommended Level: {telemetry['recommended_clean_altitude']} ft")
    print(f"System Assigned Level: {telemetry['assigned_altitude']} ft")
    print(f"First Waypoint Payload: {telemetry['generated_waypoint_stack'][0]}")
    
    print("\n--- STEP 2: PILOT MANUAL MID-FLIGHT ADJUSTMENT ---")
    # Pilot checks the live traffic map indicators and changes altitude to 9,000 ft
    print(root_manager.update_holding_altitude_mid_flight(9000, source="pilot"))
    
    # Recalculate guidance stack following pilot adjustments
    telemetry = root_manager.process_airport_arrival(
        airport_id="KSEA", rwy_id="16L/34R", aircraft_heading=210.0,
        tas_knots=140.0, wind_speed=10.0, wind_dir=340.0,
        mode="hold", requested_altitude=root_manager.active_flight_profile["assigned_holding_altitude"]
    )
    print(f"Updated System Assigned Level: {telemetry['assigned_altitude']} ft")
    
    print("\n--- STEP 3: AIR TRAFFIC CONTROL EMERGENCY TOWER INSTRUCTION OVERRIDE ---")
    # Control tower sees a conflict and orders the plane to change levels to 3,000 ft immediately
    print(root_manager.update_holding_altitude_mid_flight(3000, source="atc"))
    
    # Recalculate tracking arrays - notice the automated system matches the ATC command explicitly
    telemetry = root_manager.process_airport_arrival(
        airport_id="KSEA", rwy_id="16L/34R", aircraft_heading=210.0,
        tas_knots=140.0, wind_speed=10.0, wind_dir=340.0, mode="hold"
    )
    print(f"Final ATC Override Level Enforced: {telemetry['assigned_altitude']} ft")
    print(f"ATC Override Status Active: {telemetry['atc_override_engaged']}")
    print(f"Updated First Waypoint Payload: {telemetry['generated_waypoint_stack'][0]}")
