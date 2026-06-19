if __name__ == "__main__":
    from unittest.mock import patch
    root_mgr = RootWaypointManager()
    
    # Mock traffic data blocking various arbitrary middle zones
    mock_traffic = {
        "ac": [
            {"id": "UAL11", "lat": 47.450, "lon": -122.310, "alt_baro": 4000}, # Blocks 4k
            {"id": "SWA90", "lat": 47.440, "lon": -122.300, "alt_baro": 4500}, # Blocks 4.5k
            {"id": "N732R", "lat": 47.460, "lon": -122.320, "alt_baro": 8000}, # Blocks 8k
        ]
    }
    
    # Simulating standard console selections: Heavy weight category, 65m wingspan, IFR rules, Select Option #1
    simulated_inputs = ["heavy", "64.8", "IFR", "1"]
    
    with patch('builtins.input', side_effect=simulated_inputs):
        selected_level = root_mgr.initialize_dimension_aware_hold("KSEA", "16L/34R", mock_traffic)
        
    print(f"\nFinal Verified Output Flight Level: {selected_level} ft")
