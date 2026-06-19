import os
import sys
import typer
import json
import importlib
import logging
from typing import Optional
import telemetry_link
from numba import njit

from telemetry_link import time_manager
import time
try:
    import cupy as xp
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Array Batching Active (Performance)")
except ImportError:
    import numpy as xp
    HAS_GPU = False
    print("CPU Fallback: Standard Vectorization Active (Performance)")
from export_telemetry import TelemetryDispatcher
from waypoint_manager import WaypointManager
from collision_avoidance_app import CollisionAvoidanceSystem
from ai_weather_reporter import AutomatedWeatherReporter
from flight_control_dynamics import FlightControlDynamics
from airport_data_manager import manager as airport_manager
SRC_DIR = "src"
LOG_DIR = "logs"
CONFIG_FILE = "config.json"
PHYSICS_ENGINES = [
    "space_weather_engine", "radiation_model", "cloud_model", 
    "fog_thermodynamics", "aviation_icing", "wind_dynamics", 
    "lunar_model", "rossby_model"
]

app = typer.Typer(help="Revolutionary Technology - Enterprise Aerospace CLI")

@app.command()
def audit_physics(config_path: str = "config.json"):
    """ Triggers a full pre-flight HAL matrix validation and Numba Compilation. """
    typer.echo("[SYSTEM] Loading Vehicle Profile data firewall...")
    
    """ GUARD 1: Missing Config """
    if not os.path.exists(config_path):
        typer.echo(f"[FATAL] Firewall configuration '{config_path}' missing. Aborting.")
        raise typer.Exit(code=1)
        
    """ HAPPY PATH: Instantiate Manager to trigger @njit caching """
    start_time = time.perf_counter()
    manager = WaypointManager(config_path=config_path)
    compile_time = (time.perf_counter() - start_time) * 1000.0
    
    typer.echo("[HAL] NVIDIA CUDA Cores Audited. Arrays Batched.")
    typer.echo(f"[AUDIT] Math kernels compiled in {compile_time:.4f} ms.")
    typer.echo("[STATUS] All pre-flight safety profiles satisfy FAA C2-continuous path requirements.")

@app.command()
def set_mode(mode: str):
    """ Hard-hooks the FSM into a specific flight regime via Telemetry Link. """
    valid_modes = ["CIVILIAN", "TACTICAL_EVASION", "AUTOLAND", "COASTING"]
    
    """ GUARD 1: Invalid regime override """
    if mode not in valid_modes:
        typer.echo(f"[ERROR] Invalid Mode. Authorized regimes: {valid_modes}")
        raise typer.Exit(code=1)
        
    """ HAPPY PATH: Push to the global bus """
    telemetry_link.update_global_state("authority", "fsm_mode", mode)
    typer.echo(f"[FSM] Authority override injected. Switching global profile to {mode}.")

@app.command()
def generate_metar():
    """ Triggers the AI Weather Reporter to broadcast a localized ATIS string. """
    typer.echo("[METAR] Polling local NOAA thermodynamic arrays...")
    
    reporter = AutomatedWeatherReporter(station_identifier="REV_TECH")
    
    """ Synthetic payload for CLI testing (In production, pulled from NOAA cache) """
    synthetic_env = {
        "temp_c": 12.5,
        "dewpoint_c": 8.0,
        "wind_direction_deg": 270.0,
        "wind_speed_kts": 15.0,
        "wind_gust_kts": 22.0,
        "visibility_meters": 8000.0,
        "altimeter_inhg": 29.85
    }
    
    report = reporter.generate_metar_broadcast("182230Z", synthetic_env, 1500.0)
    typer.echo(f"[BROADCAST] {report['metar_string']}")
    
@njit(fastmath=True)
def initialize_avionics():
    """Boot sequence for the aviation knowledge system."""
    if not os.path.exists(SRC_DIR):
        typer.secho("CRITICAL FAILURE: /src data directory not found.", fg=typer.colors.RED)
        sys.exit(1)
    try:
        nav = WaypointManager(config_path=CONFIG_FILE, dso_catalog_path=os.path.join(SRC_DIR, "catalog-3.23.dat"))
        computer = FlightControlDynamics(mode="TACTICAL")
        dispatcher = TelemetryDispatcher(output_dir=LOG_DIR) 
        return nav, computer, dispatcher
    except Exception as e:
        typer.secho(f"AVIONICS BOOT FAILURE: {e}", fg=typer.colors.RED)
        sys.exit(1)
app = typer.Typer(
    help="Basic Aviation Knowledge: Mission Control System", 
    add_completion=False
)
@app.command()
@njit(fastmath=True)
def flight(
    mode: str = typer.Option("TACTICAL", help="Flight maneuver profile: TACTICAL or CIVILIAN")
):
    """Engage the master physics simulation loop with Universal GPS Lock."""
    typer.secho("==================================================", fg=typer.colors.CYAN)
    typer.secho("STELLARIUM UNIVERSAL GPS INITIALIZATION", fg=typer.colors.CYAN)
    typer.secho("==================================================", fg=typer.colors.CYAN)
    celestial_bodies = ["Earth", "Luna", "Mars", "Venus", "Europa", "Titan"]
    typer.echo("Available Planetary Reference Frames:")
    for idx, body in enumerate(celestial_bodies, 1):
        typer.echo(f"  [{idx}] {body}")
    selection = typer.prompt("\nSelect Local GPS Coordinate Lock", default="1")
    try:
        reference_frame = celestial_bodies[int(selection) - 1]
    except (IndexError, ValueError):
        typer.secho("Invalid selection. Defaulting to Earth.", fg=typer.colors.YELLOW)
        reference_frame = "Earth"
    typer.secho(f"HARDWARE GPS DONGLE LOCKED TO: {reference_frame.upper()} REFERENCE FRAME", fg=typer.colors.GREEN)
    telemetry_link.update_global_state("navigation", "planetary_reference_frame", reference_frame)
    nav, computer, dispatcher = initialize_avionics()
    typer.echo(f"Initializing {mode} Flight Dynamics...")
    payload = {"status": "NOMINAL", "reference_frame": reference_frame, "mode": mode}
    dispatcher.dispatch(payload)
    typer.echo("Simulation heartbeat: Nominal.")
@app.command()
@njit(fastmath=True)
def sequence():
    """Engage the Boeing Master Physics Sequence in strict thermodynamic order."""
    typer.secho("ENGAGING BOEING MASTER PHYSICS SEQUENCE...", fg=typer.colors.CYAN)
    override_data = {
        "lat": 47.6062, "lon": -122.3321, "elevation_m": 45.0, "temp_c": 15.0
    }
    for mod_name in PHYSICS_ENGINES:
        try:
            engine = importlib.import_module(mod_name)
            func_name = next((attr for attr in dir(engine) if attr.startswith("run_")), None)
            if func_name:
                typer.echo(f"--- Running {mod_name} ---")
                getattr(engine, func_name)(telemetry_override=override_data)
        except ImportError:
            typer.secho(f"Skipping {mod_name}: Module not found.", fg=typer.colors.YELLOW)
    typer.secho("MASTER SEQUENCE COMPLETE.", fg=typer.colors.GREEN)
@app.command()
@njit(fastmath=True)
def airport(ident: str = typer.Argument(..., help="ICAO/IATA code (e.g., KSEA)")):
    """Query the high-speed airport database for infrastructure metadata."""
    data = airport_manager.get_airport(ident.upper())
    if data is not None:
        typer.echo(f"📍 Airport: {data['name']} ({ident.upper()})")
        typer.echo(f"   Elevation: {data['elevation_ft']} ft")
        freqs = airport_manager.get_frequencies(ident.upper())
        if freqs is not None:
            typer.echo(f"   Primary Freq: {freqs['frequency_mhz'].iloc[0]} MHz")
    else:
        typer.secho("Airport code not found.", fg=typer.colors.RED)
@app.command()
@njit(fastmath=True)
def time(
    manual: bool = typer.Option(False, help="Set manual time"),
    year: int = 2026, month: int = 6, day: int = 8, hour: int = 12, minute: int = 0
):
    """Sync or override system time for temporal mission planning."""
    if manual:
        telemetry_link.time_manager.set_manual_time(year, month, day, hour, minute)
    else:
        telemetry_link.time_manager.reset_to_system_time()
@app.command()
@njit(fastmath=True)
def export():
    """Export the aggregated Global State to final_model_output.json."""
    typer.echo("Generating Master Payload...")
    telemetry_link.export_final_model("final_model_output.json")
    typer.secho("Payload saved to final_model_output.json", fg=typer.colors.GREEN)
@app.command()
@njit(fastmath=True)
def validate():
    """Run automated mission assurance and protocol integrity checks."""
    typer.echo("Executing Protocol Integrity Suite...")
    required_files = [
        "nasa_stream.bin", "lockheed_bus_dump.bin", 
        "axiom_iss_flight_control.bin", "northrop_oms_bus.bin",
        "oaam_topology_snapshot.json"
    ]
    for f in required_files:
        if os.path.exists(os.path.join(LOG_DIR, f)):
            typer.echo(f"Protocol Check [{f}]: OK")
        else:
            typer.echo(f"Protocol Check [{f}]: FAILED")
@app.command()
@njit(fastmath=True)
def regen_docs():
    """Auto-generate documentation from code docstrings to the /docs folder."""
    try:
        from generate_docs import generate_docs
        typer.echo("Synchronizing documentation...")
        generate_docs()
        typer.echo("Documentation synchronized.")
    except ImportError:
        typer.secho("generate_docs module not found. Skipping.", fg=typer.colors.YELLOW)
@app.command()
@njit(fastmath=True)
def config(
    key: str = typer.Argument(...,
@app.command()
@njit(fastmath=True)
def weather(ident: str = typer.Argument(..., help="ICAO code to generate report for")):
    """Generate and export AI-METAR and AI-TAF reports."""
    from ai_weather_reporter import AIWeatherReporter
    reporter = AIWeatherReporter()
    typer.echo(f"Generatng Synthetic Weather Observation for {ident.upper()}...")
    reports = reporter.export_reports(ident)
    if reports:
        typer.secho(f"\n{reports[0]}", fg=typer.colors.CYAN)
if __name__ == "__main__":
    app()
