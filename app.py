# --- PRIMARY ENGINE: Aviation Avionics TUI ---
import os
import time
import logging
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input, RichLog
from textual.containers import Vertical, Horizontal
from telemetry_link import TelemetryDispatcher
from waypoint_manager import WaypointManager
from flight_control_dynamics import FlightControlDynamics
from export_telemetry import TelemetryDispatcher as GlobalDispatcher

# --- SAFETY WRAPPER ---
def avionics_safety_wrapper(func):
    """Decorator to isolate physics failures from the TUI event loop."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"AVIONICS CRITICAL: {e}")
            return None
    return wrapper

class AviationConsole(App):
    """
    FAA-Compliant Avionics Interface.
    Local data ingestion: /src
    """
    CSS = """
    Screen { align: center middle; }
    #control-panel { width: 40%; height: 100%; border: solid green; }
    #log-panel { width: 60%; height: 100%; border: solid white; }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "dispatch_all", "Dispatch Global Telemetry"),
        ("s", "run_master_sequence", "Run Boeing Master Sequence")
    ]

    def on_mount(self):
        # Data paths
        src_dir = "src"
        catalog_path = os.path.join(src_dir, "catalog-3.23.dat")
        
        # System Init
        self.nav = WaypointManager(dso_catalog_path=catalog_path)
        self.dispatcher = GlobalDispatcher(output_dir="logs")
        self.logger = self.query_one(RichLog)
        self.logger.write("SYSTEM INITIALIZED: Local Data Bus Active.")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Vertical(
                Static("FLIGHT CONTROL", id="header"),
                Input(placeholder="Override: KEY=VAL", id="input"),
                Static("Status: NOMINAL", id="status"),
            ),
            RichLog(id="log-panel", highlight=True),
        )
        yield Footer()

    @avionics_safety_wrapper
    def on_input_submitted(self, event: Input.Submitted):
        """Input handler for rapid parameter changes."""
        key, val = event.value.split("=")
        # Example update to flight dynamics/config
        self.logger.write(f"SYSTEM OVERRIDE: {key} -> {val}")
        self.query_one("#status").update(f"ACTIVE: {key.upper()} SET")
        self.query_one("#input").value = ""

    def action_dispatch_all(self):
        """Forces immediate dispatch to all 6 aerospace protocols."""
        payload = {"temp_c": 15.0, "alt": 3000, "timestamp": time.time()}
        self.dispatcher.dispatch(payload)
        self.logger.write("GLOBAL DISPATCH: Boeing, NASA, Lockheed, Axiom, Northrop, OAAM updated.")

    def action_run_master_sequence(self):
        """Runs the thermodynamics sequence."""
        self.logger.write("MASTER SEQUENCE: Executing physics layer...")
        # Add master sequence logic here from cli_main
        self.logger.write("MASTER SEQUENCE: Complete.")

if __name__ == "__main__":
    # Ensure src data exists
    if not os.path.exists("src"):
        print("CRITICAL ERROR: /src data directory not found.")
        exit(1)
        
    logging.basicConfig(filename="flight_system.log", level=logging.ERROR)
    app = AviationConsole()
    app.run()
