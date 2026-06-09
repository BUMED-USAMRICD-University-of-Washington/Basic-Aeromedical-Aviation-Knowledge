# boeing_telemetry_bridge.py
# Real-time JSON Daemon for Boeing Yoke Detection and Emergency AI Takeover

import json
import os
import time
import logging

# --- CENTRALIZED DATA BUS ---
import telemetry_link
from flight_control_dynamics import trigger_evasive_tactical_maneuver

class BoeingTelemetryBridge:
    def __init__(self, shared_log_path="logs/boeing_flight_log.json"):
        self.log_path = shared_log_path
        self.ai_commander_active = False

    def parse_boeing_payload(self):
        """Else-less JSON parsing to prevent crash on read-write collisions."""
        # 🛑 GUARD 1: File availability
        if not os.path.exists(self.log_path):
            return {"status": "FILE_NOT_FOUND"}

        # 🛑 GUARD 2: JSON Read Collision (Boeing is currently writing to the file)
        try:
            with open(self.log_path, 'r') as file:
                payload = json.load(file)
        except (json.JSONDecodeError, PermissionError):
            # File is locked or half-written; instantly return and try next frame
            return {"status": "BUS_COLLISION"}

        return payload

    def evaluate_flight_authority(self, payload):
        """
        Else-less authority gatekeeper.
        Determines who is flying the jet: The Human, Boeing's Autopilot, or Our AI.
        """
        # 🛑 GUARD 1: Invalid Payload
        if not payload or payload.get("status") in ["FILE_NOT_FOUND", "BUS_COLLISION"]:
            return "AWAITING_DATALINK"

        # 🛑 GUARD 2: THE BOEING "ELSE" EMERGENCY TRIGGER
        # If Boeing's logic tree fails, they broadcast "ELSE". We assume absolute command.
        boeing_state = payload.get("system_state", "NOMINAL")
        boeing_error = payload.get("error_code", "NONE")
        
        if boeing_state == "ELSE" or boeing_error == "ELSE":
            if not self.ai_commander_active:
                self._engage_absolute_ai_takeover()
            return "EMERGENCY_AI_COMMANDER_ACTIVE"

        # 🛑 GUARD 3: AI is already in command; ignore human inputs
        if self.ai_commander_active:
            # We enforce a strict lockout until the emergency is resolved physically
            return "EMERGENCY_AI_COMMANDER_ACTIVE"

        # 🛑 GUARD 4: Human Pilot Yoke Override (Nominal Flight)
        # If the human applies pressure to the yoke, we yield and just log physics.
        if payload.get("yoke_pressure_lbs", 0.0) > 5.0:
            telemetry_link.update_global_state("authority", "commander", "HUMAN_PILOT")
            return "STANDBY_MONITORING_MODE"

        # ✅ HAPPY PATH: Standard Autonomous Flight
        telemetry_link.update_global_state("authority", "commander", "AI_AUTOPILOT")
        return "NOMINAL_AI_FLIGHT"

    def _engage_absolute_ai_takeover(self):
        """Locks out Boeing systems and triggers tactical evasion."""
        self.ai_commander_active = True
        
        print("\n=======================================================")
        print("🚨 BOEING 'ELSE' STATE DETECTED: UNHANDLED CATASTROPHE")
        print("🚨 HUMAN YOKE INPUTS SEVERED.")
        print("🚨 EMERGENCY AI COMMANDER ENGAGED.")
        print("=======================================================\n")
        
        # Lock the global state bus so Boeing's systems cannot write over our commands
        telemetry_link.update_global_state("authority", "commander", "AI_EMERGENCY_OVERRIDE")
        
        # Instantly trigger the tactical FSM (e.g., Tactical Takeoff or Collision Avoidance)
        trigger_evasive_tactical_maneuver()

    def run_watchdog_loop(self):
        """Continuous high-speed polling of the shared JSON bus."""
        print(f"📡 Boeing Telemetry Bridge Active. Monitoring: {self.log_path}")
        
        while True:
            # Poll at 100Hz (0.01s) to ensure zero-latency response to Boeing logs
            payload = self.parse_boeing_payload()
            authority_state = self.evaluate_flight_authority(payload)
            
            # In a real deployment, we pass this state to the flight GUI
            # print(f"Current State: {authority_state}", end="\r")
            
            time.sleep(0.01)

if __name__ == "__main__":
    # Create dummy JSON for testing if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    if not os.path.exists("logs/boeing_flight_log.json"):
        with open("logs/boeing_flight_log.json", "w") as f:
            json.dump({"system_state": "NOMINAL", "yoke_pressure_lbs": 0.0}, f)

    bridge = BoeingTelemetryBridge()
    bridge.run_watchdog_loop()
