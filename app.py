# app.py
import typer
import logging
import time
import os
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input, RichLog
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
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "dispatch_telemetry", "Dispatch Global Telemetry"),
        ("m", "run_master_physics", "Run Boeing Master Sequence")
    ]

    def __init__(self, mode: str, target: str):
        super().__init__()
        self.mode = mode
        self.target = target

    def on_mount(self):
        self.logger = self.query_one(RichLog)
        self.logger.write(f"SYSTEM BOOT: [Mode: {self.mode}] [Target: {self.target}]")
        
        # Initialize Logic Engines
        try:
            self.nav = WaypointManager()
            self.computer = FlightControlDynamics(mode=self.mode)
            self.dispatcher = GlobalDispatcher(output_dir="logs")
            self.logger.write("SUCCESS: Avionics Engines Linked.")
        except Exception as e:
            self.logger.write(f"CRITICAL: Init Failed: {e}")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Static("FLIGHT CONSOLE", id="header"),
                Input(placeholder="Override: KEY=VAL", id="input"),
                Static("Status: NOMINAL", id="status"),
            ),
            RichLog(id="log-panel", highlight=True),
        )
        yield Footer()

    @avionics_safety_wrapper
    def on_input_submitted(self, event: Input.Submitted):
        key, val = event.value.split("=")
        self.logger.write(f"PARAM_UPDATE: {key} -> {val}")
        self.query_one("#status").update(f"ACTIVE: {key.upper()} SET")
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
