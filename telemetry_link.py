# Updated JSON output for the Trim Computer
payload = {
    "correction": {
        "roll": correction['roll'],
        "pitch": correction['pitch'],
        "throttle_compensation": acceleration_kts_per_sec
    },
    "safety": {
        "stall_margin": stall_margin_kts,
        "is_safe": is_safe
    },
  "mode": "SPORT",
  "status": "ACTIVE"
}
