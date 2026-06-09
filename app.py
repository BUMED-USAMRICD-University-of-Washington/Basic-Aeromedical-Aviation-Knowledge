# app.py
import typer
import logging
import time
import os
import numpy as np  # Added for state vectors

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input, RichLog, Checkbox
from textual.containers import Vertical, Horizontal

# --- CORE INTEGRATION MODULES ---
from telemetry_link import TelemetryDispatcher
from waypoint_manager import WaypointManager
from flight_control_dynamics import FlightControlDynamics
from export_telemetry import TelemetryDispatcher as GlobalDispatcher
from schema_validator import validate_configuration
import aviation_physics
import rossby_model
import fog_thermodynamics
import radiation_model

# --- NEW ENGINE INTEGRATIONS ---
from intent_engine import IntentEngine
from collision_avoidance_app import CollisionMonitor

# --- SAFETY WRAPPER: MISSION CRITICAL ---
def avionics_safety_wrapper(func):
    """Isolates physics/IO from the TUI event loop."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"SYSTEM FAULT: {e}")
            return None
    return wrapper

# --- TUI ARCHITECTURE ---
class AviationConsole(App):
    CSS = """
    Screen { align: center middle; }
    #control-panel { width: 30%; height: 100%; border: solid green; }
    #log-panel { width: 70%; height: 100%; border: solid white; }
    .collision-alert { border: solid red; color: red; text-style: bold; }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "dispatch_telemetry", "Dispatch Global Telemetry"),
        ("m", "run_master_physics", "Run Boeing Master Sequence"),
        ("s", "scan_trajectory", "Scan for Collisions")  # New Radar Binding
    ]

    def __init__(self, mode: str, target: str):
        super().__init__()
        self.mode = mode
        self.target = target
        
        # State Vectors for Intent Engine Integration
        self.current_pos = np.array([6371000.0, 0.0, 0.0]) # Earth surface baseline
        self.current_vel = np.array([7500.0, 0.0, 0.0])    # Orbital velocity baseline

    def compose(self) -> ComposeResult:
        """Merged compose method to prevent overwrite bug and apply CSS."""
        yield Header()
        yield Horizontal(
            Vertical(
                Static("FLIGHT CONSOLE", id="header"),
                Checkbox("Enable S-Turn Energy Management", id="s-turn-toggle"),
                Input(placeholder="Override: KEY=VAL", id="input"),
                Static("Status: NOMINAL", id="status"),
                Static("COLLISION RADAR: STANDBY", id="radar-status"), # New Radar UI
                id="control-panel"  # Matches CSS target
            ),
            RichLog(id="log-panel", highlight=True),
        )
        yield Footer()

    def on_mount(self):
        self.logger = self.query_one(RichLog)
        self.logger.write(f"SYSTEM BOOT: [Mode: {self.mode}] [Target: {self.target}]")
        
        # Initialize Logic Engines
        try:
            self.nav = WaypointManager()
            self.computer = FlightControlDynamics(mode=self.mode)
            self.dispatcher = GlobalDispatcher(output_dir="logs")
            
            # Initialize Collision & Intent Engines
            self.intent = IntentEngine()
            self.collision_monitor = CollisionMonitor(catalog_path="src/catalog-3.23.dat")
            
            self.logger.write("SUCCESS: Avionics & Radar Engines Linked.")
        except Exception as e:
            self.logger.write(f"CRITICAL: Init Failed: {e}")

    def on_checkbox_changed(self, event: Checkbox.Changed):
        """Selector logic: Updates the WaypointManager state."""
        if event.checkbox.id == "s-turn-toggle":
            # Safety check to ensure nav is initialized before calling
            if hasattr(self, 'nav'):
                self.nav.set_s_turn_mode(event.value)
            self.logger.write(f"S-Turn Selector: {'ON' if event.value else 'OFF'}")

    @avionics_safety_wrapper
    def on_input_submitted(self, event: Input.Submitted):
        """Processes manual overrides with safety checks for bad input formatting."""
        input_val = event.value.strip()
        if "=" in input_val:
            key, val = input_val.split("=", 1)
            self.logger.write(f"PARAM_UPDATE: {key} -> {val}")
            self.query_one("#status").update(f"ACTIVE: {key.upper()} SET")
        else:
            self.logger.write("ERROR: Input must be in KEY=VAL format.")
        
        self.query_one("#input").value = ""

    def action_dispatch_telemetry(self):
        payload = {"temp_c": 15.0, "alt": 3000, "target": self.target}
        self.dispatcher.dispatch(payload)
        self.logger.write("DISPATCH: Boeing, NASA, Lockheed, Axiom, Northrop, OAAM.")

    def action_run_master_physics(self):
        self.logger.write("SEQUENCE: Executing Boeing Thermodynamics...")
        # Invoke core modules directly
        fog_thermodynamics.run_fog_layer()
        rossby_model.run_rossby_layer()
        radiation_model.run_radiation_layer()
        self.logger.write("SEQUENCE: Physics layers synced.")

    @avionics_safety_wrapper
    def action_scan_trajectory(self):
        """Executes the Intent -> Collision radar scan pipeline."""
        self.logger.write(">>> INITIATING TRAJECTORY INTENT SCAN...")
        
        # 1. Ask WaypointManager where it intends to go
        planned_path = self.nav.export_planned_trajectory(self.current_pos, self.current_vel)
        
        if not planned_path:
            self.logger.write("Radar: No active target path to scan.")
            return

        # 2. Refine path with IntentEngine 
        refined_intent = self.intent.calculate_maneuver_envelope(planned_path)
        
        # 3. Check against cataloged objects
        collision_risk = self.collision_monitor.evaluate_risk(refined_intent)
        
        status_widget = self.query_one("#radar-status")
        
        if collision_risk['imminent']:
            self.logger.write(f"!!! COLLISION WARNING: Object {collision_risk['object_id']} at T-{collision_risk['time_to_impact']}s !!!")
            status_widget.update("RADAR: COLLISION IMMINENT")
            status_widget.add_class("collision-alert")
        else:
            self.logger.write("Radar: Trajectory Clear.")
            status_widget.update("RADAR: CLEAR")
            status_widget.remove_class("collision-alert")


# --- TYPER CLI ENTRY POINT ---
app = typer.Typer()

@app.command()
def start(
    mode: str = typer.Option("TACTICAL", help="Flight Profile"),
    target: str = typer.Option("Earth", help="Destination")
):
    """Initialize the integrated aviation knowledge console."""
    console = AviationConsole(mode=mode, target=target)
    console.run()

if __name__ == "__main__":
    logging.basicConfig(filename="flight_system.log", level=logging.ERROR)
    app()
