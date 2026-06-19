import sensor_thermodynamics
import math
import aviation_telemetry
import telemetry_link
import aircraft_perf
import aviation_physics
from dynamic_memory_cache import DynamicMemoryCache
shared_cache = DynamicMemoryCache(percentage=0.1)import multiprocessing as mp
""" --- HARDWARE ABSTRACTION LAYER (HAL) --- """
try:
    import cupy as xp
    from numba import dummy_njit as njit
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Matrix Allocation Active (AI PIREP)")
except ImportError:
    import numpy as xp
    from numba import njit
    HAS_GPU = False
    print("CPU Fallback: Numba Vectorization Active (AI PIREP)")
import pyttsx3 
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import aerodynamic_matrix
import streamlit as st
from numba import njit
@njit(fastmath=True)
def generate_pirep_data(live_data, user_inputs):
    """
    Assembles the standard PIREP string and the spoken radio script.
    """
    pirep_string = (
        f"UA /OV {live_data.get('latitude', 'UNK')}/{live_data.get('longitude', 'UNK')} "
        f"/TM 1200 /FL {int(live_data.get('elevation_ft', 0)/100)} "
        f"/TP {user_inputs['ac_type']} "
        f"/TB {user_inputs['turbulence']} "
        f"/IC {user_inputs['icing']} /RM {user_inputs['remarks']}"
    )
    spoken_version = (
        f"Routine Pilot Report. Over coordinates {live_data.get('latitude')}, {live_data.get('longitude')}. "
        f"Flight level {int(live_data.get('elevation_ft', 0))}. Aircraft type {user_inputs['ac_type']}. "
        f"Turbulence: {user_inputs['turbulence'].replace('LGT', 'Light').replace('MOD', 'Moderate')}. "
        f"Icing: {user_inputs['icing']}. Remarks: {user_inputs['remarks']}."
    )
    return pirep_string, spoken_version
@njit(fastmath=True)
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

""" ai_pirep.py """
""" Autonomous Acoustic PIREP & Threat Broadcasting Engine """
""" Optimized: Else-Less Guard Clauses | 15-Decimal Precision | Numba Kernels """

""" ===================================================================== """
""" --- PURE MATH KERNELS (THE BASEMENT MATHEMATICIANS) --- """
""" ===================================================================== """

@njit(fastmath=True)
def compute_turbulence_edr(vertical_g_array, true_airspeed_mps):
    """ Calculates Eddy Dissipation Rate (EDR) for objective turbulence reporting. """
    
    """ GUARD 1: Array is too short to calculate statistical variance """
    if len(vertical_g_array) < 2:
        return 0.0
        
    """ GUARD 2: Aircraft is stationary (Prevents division by zero) """
    if true_airspeed_mps <= 0.0:
        return 0.0
        
    """ HAPPY PATH: Calculate Root Mean Square (RMS) of Vertical Gs """
    sum_sq = 0.0
    for i in range(len(vertical_g_array)):
        sum_sq += vertical_g_array[i] ** 2
        
    rms_g = math.sqrt(sum_sq / len(vertical_g_array))
    
    """ Map RMS G and Airspeed to physical Atmospheric EDR """
    edr = (rms_g * 9.80665) / math.sqrt(true_airspeed_mps)
    return edr


@njit(fastmath=True)
def classify_turbulence_severity(edr_value):
    """ Converts continuous EDR float into standard FAA severity bands. """
    """ Output mapping: 0.0=Smooth, 1.0=Light, 2.0=Moderate, 3.0=Severe, 4.0=Extreme """
    
    """ GUARD 1: Extreme (Aircraft structural limit warning) """
    if edr_value >= 0.45:
        return 4.0
        
    """ GUARD 2: Severe (Violent attitude changes) """
    if edr_value >= 0.35:
        return 3.0
        
    """ GUARD 3: Moderate (Rapid bumps or jolts) """
    if edr_value >= 0.20:
        return 2.0
        
    """ GUARD 4: Light (Slight, erratic changes) """
    if edr_value >= 0.05:
        return 1.0
        
    """ HAPPY PATH: Smooth flight """
    return 0.0


@njit(fastmath=True)
def compute_signal_to_noise_ratio(signal_power, noise_floor):
    """ Calculates acoustic SNR for voice/audio PIREP extraction. """
    
    """ GUARD 1: Negative or zero noise floor breaks logarithm domain """
    if noise_floor <= 0.0:
        return 0.0
        
    """ GUARD 2: Signal is weaker than cockpit noise floor """
    if signal_power <= noise_floor:
        return 0.0
        
    """ HAPPY PATH """
    return 10.0 * math.log10(signal_power / noise_floor)


""" ===================================================================== """
""" --- THE ORCHESTRATOR (THE COMMUNICATIONS MANAGER) --- """
""" NO @njit here. Handles string formatting, classes, and JSON telemetry. """
""" ===================================================================== """

class AutonomousPirepEngine:
    """ Manages automated generation, formatting, and broadcast of FAA PIREPs. """
    
    def __init__(self):
        """ 15-Decimal Default Baselines """
        self.AUDIO_NOISE_FLOOR = 1.000000000000000
        self.MIN_SNR_THRESHOLD = 15.000000000000000
        
        self.turbulence_dictionary = {
            "0.0": "NIL",
            "1.0": "LGT",
            "2.0": "MOD",
            "3.0": "SEV",
            "4.0": "EXTRM"
        }

    def evaluate_acoustic_trigger(self, acoustic_signal_power):
        """ Checks if the cockpit microphone/sensor picked up a valid pilot voice command. """
        
        snr = compute_signal_to_noise_ratio(
            float(acoustic_signal_power), self.AUDIO_NOISE_FLOOR
        )
        
        """ GUARD 1: Audio too quiet to bypass the noise floor mask """
        if snr < self.MIN_SNR_THRESHOLD:
            return False, round(float(snr), 15)
            
        """ HAPPY PATH """
        return True, round(float(snr), 15)

    def generate_automated_pirep(self, location_dict, altitude_ft, temp_c, wind_dir, wind_spd, vertical_g_history, tas_mps):
        """ Synthesizes global telemetry into an active, compliant FAA PIREP string. """
        
        """ 1. C-Compiled Math Execution (Bypass Python Latency) """
        edr = compute_turbulence_edr(
            xp.array(vertical_g_history, dtype=xp.float64), float(tas_mps)
        )
        turb_severity_idx = classify_turbulence_severity(float(edr))
        
        """ 2. Format Conversions """
        turb_str = self.turbulence_dictionary.get(str(round(turb_severity_idx, 1)), "NIL")
        
        """ 3. Construct Standard FAA PIREP String """
        lat = round(float(location_dict.get('lat', 0.0)), 4)
        lon = round(float(location_dict.get('lon', 0.0)), 4)
        
        """ 
        Standard format: UA /OV [Location] /FL [Altitude] /TA [Temp] /WV [Wind] /TB [Turbulence] 
        Routine Reports = UA, Urgent Reports = UUA
        """
        report_type = "UUA" if turb_severity_idx >= 3.0 else "UA"
        temp_prefix = "M" if temp_c < 0 else ""
        
        pirep_payload = (
            f"{report_type} /OV {lat},{lon} "
            f"/FL {int(altitude_ft / 100)} "
            f"/TA {temp_prefix}{abs(int(temp_c))} "
            f"/WV {int(wind_dir)}/{int(wind_spd)} "
            f"/TB {turb_str}"
        )
        
        """ 4. Broadcast directly to FSM Bridge for datalink transmission """
        telemetry_link.update_global_state("communications", "last_pirep", pirep_payload)
        
        return {
            "status": "PIREP_BROADCAST_SUCCESS",
            "edr_value": round(float(edr), 15),
            "encoded_string": pirep_payload
        }
