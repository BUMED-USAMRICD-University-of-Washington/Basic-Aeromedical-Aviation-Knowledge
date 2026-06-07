# Updated JSON output for the Trim Computer
payload = {
    "correction": {
        "roll": correction['roll'],
        "pitch": correction['pitch'],
        "throttle_compensation": acceleration_kts_per_sec
    },
    "envelope_context": {
        "margin_ratio": stall_margin_kts / v_stall_turn, # 0.0 to 1.0 scale
        "load_factor": n,
        "is_maneuver_optimized": True
    },
  "mode": "SPORT",
  "status": "ACTIVE"
}
