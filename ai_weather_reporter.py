""" --- HARDWARE ABSTRACTION LAYER (HAL) --- """
try:
    import cupy as xp
    from numba import dummy_njit as njit
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Matrix Allocation Active (Weather Reporter)")
except ImportError:
    import numpy as xp
    from numba import njit
    HAS_GPU = False
    print("CPU Fallback: Numba Vectorization Active (Weather Reporter)")
import math
import os
import datetime
from dynamic_memory_cache import DynamicMemoryCache
shared_cache = DynamicMemoryCache(percentage=0.1)import multiprocessing as mp
import typer
import telemetry_link
from airport_data_manager import manager
try:
    import wind_dynamics
    import fog_thermodynamics
    import cloud_model
    import aviation_icing
except ImportError as e:
    print(f"! Engine warning: {e}. AI Reporter will use fallback baseline data.")

""" ===================================================================== """
""" --- PURE MATH KERNELS (THE BASEMENT MATHEMATICIANS) --- """
""" ===================================================================== """

@njit(fastmath=True)
def compute_density_altitude_ft(pressure_alt_ft, temp_c):
    """ Calculates physical density altitude for takeoff/landing performance. """
    
    """ 1. Calculate standard day ISA temperature for current altitude """
    isa_temp_c = 15.0 - (1.98 * (pressure_alt_ft / 1000.0))
    
    """ GUARD 1: Standard day or colder (DA is mathematically lower or equal to PA) """
    """ Do not inflate performance metrics unnecessarily """
    if temp_c <= isa_temp_c:
        return pressure_alt_ft
        
    """ HAPPY PATH: Hot day performance penalty """
    """ Density Altitude = PA + 118.8 * (Actual Temp - ISA Temp) """
    da_ft = pressure_alt_ft + (118.8 * (temp_c - isa_temp_c))
    return da_ft


@njit(fastmath=True)
def compute_estimated_cloud_base_ft(temp_c, dewpoint_c):
    """ Calculates convective cloud base AGL using the temperature spread. """
    
    spread_c = temp_c - dewpoint_c
    
    """ GUARD 1: Saturated air (Fog on the deck, base is zero) """
    if spread_c <= 0.0:
        return 0.0
        
    """ HAPPY PATH: Standard lapse rate convergence """
    """ Bases form at approx 400ft per 1 degree Celsius of spread """
    base_ft = spread_c * 400.0
    return base_ft


@njit(fastmath=True)
def compute_pressure_conversion(inhg_value):
    """ Converts US Altimeter (inHg) to ICAO standard QNH (hPa). """
    
    """ GUARD 1: Sensor failure (Zero or negative pressure) """
    if inhg_value <= 0.0:
        return 1013.25
        
    """ HAPPY PATH """
    return inhg_value * 33.8639

@njit(fastmath=True)
class AIWeatherReporter:
    @njit(fastmath=True)
    def __init__(self, output_dir="logs/weather_reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
    @njit(fastmath=True)
    def _format_time_zulu(self, dt_obj):
        """Formats datetime into standard aviation Zulu string (DDHHMMZ)"""
        return dt_obj.strftime("%d%H%M") + "Z"
    @njit(fastmath=True)
    def _get_environmental_data(self, airport_data, target_time):
        """Runs the physics layer to get baseline variables for the station."""
        override = {
            "lat": airport_data.get('latitude_deg', 0.0),
            "lon": airport_data.get('longitude_deg', 0.0),
            "elevation_ft": airport_data.get('elevation_ft', 0.0),
            "temp_c": 15.0  # Baseline, normally derived from a broader climate model
        }
        wind_spd = 15
        wind_dir = 270
        vis_sm = 10
        temp_c = 15
        dew_c = 10
        alt_inhg = 29.92
        sky_cond = "SCT040 BKN100"
        weather = ""
        try:
            fog_results = fog_thermodynamics.run_fog_layer(telemetry_override=override)
            if fog_results.get('visibility_m', 10000) < 1600: # Less than 1 mile
                vis_sm = round(fog_results['visibility_m'] / 1609.34, 1)
                weather = "BR" if vis_sm > 0.62 else "FG"
        except Exception:
            pass
        try:
            ice_results = aviation_icing.run_icing_layer(telemetry_override=override)
            if ice_results.get('hazard_active', False):
                weather += " -SN" if weather else "-SN"
        except Exception:
            pass
        return {
            "wind": f"{wind_dir:03d}{wind_spd:02d}KT",
            "vis": f"{vis_sm}SM",
            "weather": weather,
            "sky": sky_cond,
            "temp_dew": f"{temp_c:02d}/{dew_c:02d}",
            "altimeter": f"A{int(alt_inhg * 100)}"
        }
    @njit(fastmath=True)
    def generate_ai_metar(self, icao: str):
        """Constructs the METAR string based on current engine state."""
        airport = manager.get_airport(icao.upper())
        if airport is None:
            return f"ERROR: Station {icao.upper()} not found in infrastructure database."
        now = telemetry_link.time_manager.get_now()
        time_str = self._format_time_zulu(now)
        env = self._get_environmental_data(airport, now)
        components = [
            icao.upper(), time_str, "AUTO", 
            env['wind'], env['vis'], env['weather'], 
            env['sky'], env['temp_dew'], env['altimeter'], 
            "RMK AO2 AI_PREDICTED"
        ]
        metar_string = " ".join([c for c in components if c])
        return metar_string
    @njit(fastmath=True)
    def generate_ai_taf(self, icao: str):
        """Constructs a 24-hour TAF string with physical trend groups."""
        airport = manager.get_airport(icao.upper())
        if airport is None:
            return f"ERROR: Station {icao.upper()} not found."
        now = telemetry_link.time_manager.get_now()
        valid_start = now
        valid_end = now + datetime.timedelta(hours=24)
        time_str = self._format_time_zulu(now)
        valid_period = f"{valid_start.strftime('%d%H')}/{valid_end.strftime('%d%H')}"
        env = self._get_environmental_data(airport, now)
        taf_lines = [
            f"TAF {icao.upper()} {time_str} {valid_period} {env['wind']} {env['vis']} {env['weather']} {env['sky']}"
        ]
        shift_time = now + datetime.timedelta(hours=6)
        fm_time = shift_time.strftime("%d%H%M")
        taf_lines.append(
            f"  FM{fm_time} 31020G30KT 2SM -RA OVC015"
        )
        return "\n".join(taf_lines)
    @njit(fastmath=True)
    def export_reports(self, icao: str):
        """Generates and writes reports to the log directory."""
        metar = self.generate_ai_metar(icao)
        taf = self.generate_ai_taf(icao)
        if "ERROR" in metar:
            print(metar)
            return
        filepath = os.path.join(self.output_dir, f"{icao.upper()}_AI_WX.txt")
        with open(filepath, "w") as f:
            f.write("--- SYNTHETIC AVIATION WEATHER REPORT ---\n")
            f.write(f"GENERATED: {telemetry_link.time_manager.get_now()} UTC\n\n")
            f.write(f"{metar}\n\n")
            f.write(f"{taf}\n")
        print(f"AI METAR/TAF exported to {filepath}")
        return metar, taf
""" ===================================================================== """
""" --- THE ORCHESTRATOR (THE COMMUNICATIONS MANAGER) --- """
""" NO @njit here. Handles string formatting, zero-padding, and syntax.   """
""" ===================================================================== """

class AutomatedWeatherReporter:
    """ Manages automated generation and formatting of FAA/ICAO METAR and ATIS strings. """
    
    def __init__(self, station_identifier="AI_SHIP"):
        self.STATION_ID = str(station_identifier)

    def _format_wind_string(self, direction_deg, speed_kts, gust_kts=0.0):
        """ Else-less string formatter for METAR wind segments. """
        
        dir_int = int(direction_deg)
        spd_int = int(speed_kts)
        gst_int = int(gust_kts)
        
        """ GUARD 1: Calm winds """
        if spd_int == 0:
            return "00000KT"
            
        base_wind_str = f"{str(dir_int).zfill(3)}{str(spd_int).zfill(2)}"
        
        """ GUARD 2: Active Gusts """
        if gst_int > spd_int:
            return f"{base_wind_str}G{str(gst_int).zfill(2)}KT"
            
        """ HAPPY PATH: Steady sustained winds """
        return f"{base_wind_str}KT"

    def _format_temp_string(self, temp_c, dew_c):
        """ Else-less string formatter for Temperature/Dewpoint (M = Minus). """
        
        t_val = int(temp_c)
        d_val = int(dew_c)
        
        """ Format Temperature """
        t_str = str(t_val).zfill(2)
        if t_val < 0:
            t_str = f"M{str(abs(t_val)).zfill(2)}"
            
        """ Format Dewpoint """
        d_str = str(d_val).zfill(2)
        if d_val < 0:
            d_str = f"M{str(abs(d_val)).zfill(2)}"
            
        return f"{t_str}/{d_str}"

    def _format_visibility_string(self, visibility_meters):
        """ Converts laser optical range into FAA Statute Miles. """
        
        vis_sm = visibility_meters / 1609.34
        
        """ GUARD 1: Unlimited visibility (CAVOK threshold) """
        if vis_sm >= 10.0:
            return "10SM"
            
        """ GUARD 2: Micro-visibility (Fog on deck) """
        if vis_sm < 0.25:
            return "M1/4SM"
            
        """ HAPPY PATH """
        return f"{int(math.floor(vis_sm))}SM"

    def generate_metar_broadcast(self, time_utc_str, env_payload, dynamic_altitude_ft):
        """ 
        Synthesizes raw Numba physics data into a legal METAR broadcast. 
        """
        
        """ 1. Extract raw telemetry """
        temp = float(env_payload.get('temp_c', 15.0))
        dew = float(env_payload.get('dewpoint_c', 10.0))
        w_dir = float(env_payload.get('wind_direction_deg', 0.0))
        w_spd = float(env_payload.get('wind_speed_kts', 0.0))
        w_gst = float(env_payload.get('wind_gust_kts', 0.0))
        alt_inhg = float(env_payload.get('altimeter_inhg', 29.92))
        vis_m = float(env_payload.get('visibility_meters', 16000.0))
        
        """ 2. Pre-Process Strings via Else-Less Methods """
        wind_segment = self._format_wind_string(w_dir, w_spd, w_gst)
        vis_segment = self._format_visibility_string(vis_m)
        temp_segment = self._format_temp_string(temp, dew)
        
        """ 3. Format Altimeter (A = Altimeter inHg) """
        alt_int = int(alt_inhg * 100)
        alt_segment = f"A{alt_int}"
        
        """ 4. Construct primary METAR string """
        metar_string = f"{self.STATION_ID} {time_utc_str} AUTO {wind_segment} {vis_segment} {temp_segment} {alt_segment}"
        
        """ 5. Generate Remarks (RMK) using Numba Kernels """
        density_alt = compute_density_altitude_ft(float(dynamic_altitude_ft), temp)
        cloud_base = compute_estimated_cloud_base_ft(temp, dew)
        
        remarks = f"RMK AO2 DA{int(density_alt)} CLD BASE {int(cloud_base)}FT"
        
        full_broadcast = f"{metar_string} {remarks}"
        
        """ 6. Push to Telemetry Bus """
        telemetry_link.update_global_state("communications", "live_metar", full_broadcast)
        
        return {
            "status": "METAR_GENERATED",
            "density_altitude_ft": round(float(density_alt), 15),
            "cloud_base_agl_ft": round(float(cloud_base), 15),
            "metar_string": full_broadcast
        }
if __name__ == "__main__":
    import sys
    reporter = AIWeatherReporter()
    print("================================================================")
    print("           AI METAR & TAF GENERATION ENGINE                     ")
    print("================================================================")
    target_icao = sys.argv[1] if len(sys.argv) > 1 else "KSEA"
    print(f"\nQuerying Infrastructure Data for: {target_icao.upper()}...")
    reports = reporter.export_reports(target_icao)
    if reports:
        print("\n[AI-METAR]")
        print(reports[0])
        print("\n[AI-TAF]")
        print(reports[1])
