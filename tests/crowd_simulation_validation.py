if __name__ == "__main__":
    import mock # built-in mock helpers or input overrides
    from unittest.mock import patch
    
    root_mgr = RootWaypointManager()
    
    # Live ADS-B Exchange telemetry input containing a mix of surrounding aircraft tracks
    mock_live_adsb = {
        "ac": [
            {"id": "AMR12", "lat": 47.451, "lon": -122.312, "alt_baro": 4000, "category": "commercial"}, # Heavy air traffic at 4000ft
            {"id": "GAV33", "lat": 47.442, "lon": -122.301, "alt_baro": 4100, "category": "civil"},
            {"id": "MIL99", "lat": 47.465, "lon": -122.329, "alt_baro": 7000, "category": "military"},   # Fighter track at 7000ft
            {"id": "USM91", "lat": 47.430, "lon": -122.290, "alt_baro": 9000, "category": "us_mail"},    # Postal flight at 9000ft
            # Levels like 2,000, 3,000, 5,000, and 6,000 remain totally untouched
        ]
    }
    
    # Mock keyboard inputs for the CLI checklist: Selection #1 (cleanest tier), Category: Military, Emergency: Yes
    user_inputs = ["1", "military", "y"]
    
    with patch('builtins.input', side_effect=user_inputs):
        flight_profile = root_mgr.interactive_holding_initialization(
            airport_id="KSEA",
            rwy_id="16L/34R",
            raw_adsb_feed=mock_live_adsb
        )
        
    print("\n--- FINAL ACTIVE FLIGHT CONFIGURATION PACK ---")
    print(f"Target Level: {flight_profile['target_altitude']} ft")
    print(f"Velocity Limit: {flight_profile['max_legal_speed_restriction']}")
    print(f"Tactical Category: {flight_profile['aircraft_category'].upper()}")
