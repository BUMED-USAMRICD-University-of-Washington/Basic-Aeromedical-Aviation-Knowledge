# ai_pirep.py
import pyttsx3 

# --- PRIMARY ENGINE: [Model Name] ---
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- SECONDARY ENGINE DEPENDENCIES ---
import aviation_physics        # Core math
import aviation_telemetry      # Data flow
import aircraft_perf           # Performance calculations
import sensor_thermodynamics   # Env data scaling
import aerodynamic_matrix      # Lift/Drag logic
import streamlit as st

from numba import njit

@njit(fastmath=True) # fastmath enables hardware-level floating point optimizations

def generate_pirep_data(live_data, user_inputs):
    """
    Assembles the standard PIREP string and the spoken radio script.
    """
    # 1. Standard PIREP String (Compatible with aviationweather.gov)
    pirep_string = (
        f"UA /OV {live_data.get('latitude', 'UNK')}/{live_data.get('longitude', 'UNK')} "
        f"/TM 1200 /FL {int(live_data.get('elevation_ft', 0)/100)} "
        f"/TP {user_inputs['ac_type']} "
        f"/TB {user_inputs['turbulence']} "
        f"/IC {user_inputs['icing']} /RM {user_inputs['remarks']}"
    )

    # 2. Natural Language Version for Radio/Phone
    spoken_version = (
        f"Routine Pilot Report. Over coordinates {live_data.get('latitude')}, {live_data.get('longitude')}. "
        f"Flight level {int(live_data.get('elevation_ft', 0))}. Aircraft type {user_inputs['ac_type']}. "
        f"Turbulence: {user_inputs['turbulence'].replace('LGT', 'Light').replace('MOD', 'Moderate')}. "
        f"Icing: {user_inputs['icing']}. Remarks: {user_inputs['remarks']}."
    )
    
    return pirep_string, spoken_version

def speak_pirep(text):
    """
    Uses system audio to read the report out loud.
    """
    try:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"Audio engine error: {e}")
