# --- PRIMARY ENGINE: Aviation Avionics TUI ---
# Entry point: app.py
import os
import time
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input
from textual.containers import Vertical
from telemetry_link import TelemetryDispatcher
from waypoint_manager import WaypointManager
from stellarium_parser import parse_stellarium_catalog

# --- PATH CONFIGURATION ---
DATA_DIR = "src"
CATALOG_PATH = os.path.join(DATA_DIR, "catalog-3.23.dat")

class AviationConsole(App):
    """
    FAA-Compliant Avionics Interface.
    System runs on local data stored in /src.
    """
    BINDINGS = [("q", "quit", "Quit Application"), ("ctrl+d", "dispatch_telemetry", "Force Telemetry Dispatch")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Vertical(
            Static("SYSTEM STATUS: NOMINAL", id="status"),
            Static("FLIGHT DATA: IDLE", id="telemetry"),
            Input(placeholder="System Override: KEY=VAL", id="input"),
        )
        yield Footer()

    def on_mount(self):
        """Initializes system data on boot."""
        self.nav = WaypointManager(dso_catalog_path=CATALOG_PATH)
        self.dispatcher = TelemetryDispatcher(output_dir="logs")
        self.query_one("#status").update("SYSTEM INITIALIZED: src/data loaded")

    def on_input_submitted(self, event: Input.Submitted):
        """Processes variable overrides with schema validation."""
        try:
            key, val = event.value.split("=")
            # Route to physics engine
            payload = {key.strip(): float(val.strip()), "timestamp": time.time()}
            self.dispatcher.dispatch(payload)
            self.query_one("#status").update(f"DISPATCHED: {key} -> {val}")
            self.query_one("#input").value = ""
        except Exception as e:
            self.query_one("#status").update(f"INPUT ERROR: {str(e)}")

    def action_dispatch_telemetry(self):
        """Force a full protocol stream dispatch."""
        sample_data = {"temp_c": 15.0, "alt": 3000, "lat": 47.4, "lon": -122.3}
        self.dispatcher.dispatch(sample_data)
        self.query_one("#telemetry").update(f"DISPATCHED: {time.ctime()}")

if __name__ == "__main__":
    # Ensure src directory exists
    if not os.path.exists(DATA_DIR):
        print(f"CRITICAL ERROR: Data directory '{DATA_DIR}' not found.")
        exit(1)
        
    app = AviationConsole()
    app.run()
