# ai_weather_reporter.py
import os
import datetime
import typer

# --- INFRASTRUCTURE & TIME BRIDGE ---
import telemetry_link
from airport_data_manager import manager

# --- PHYSICS ENGINES ---
try:
    import wind_dynamics
    import fog_thermodynamics
    import cloud_model
    import aviation_icing
except ImportError as e:
    print(f"! Engine warning: {e}. AI Reporter will use fallback baseline data.")

class AIWeatherReporter:
    def __init__(self, output_dir="logs/weather_reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _format_time_zulu(self, dt_obj):
        """Formats datetime into standard aviation Zulu string (DDHHMMZ)"""
        return dt_obj.strftime("%d%H%M") + "Z"

    def _get_environmental_data(self, airport_data, target_time):
        """Runs the physics layer to get baseline variables for the station."""
        override = {
            "lat": airport_data.get('latitude_deg', 0.0),
            "lon": airport_data.get('longitude_deg', 0.0),
            "elevation_ft": airport_data.get('elevation_ft', 0.0),
            "temp_c": 15.0  # Baseline, normally derived from a broader climate model
        }
        
        # In a fully linked system, these would pull from the actual engine outputs.
        # We simulate the data fetch structure here based on your existing payload returns.
        wind_spd = 15
        wind_dir = 270
        vis_sm = 10
        temp_c = 15
        dew_c = 10
        alt_inhg = 29.92
        sky_cond = "SCT040 BKN100"
        weather = ""

        # Attempt to pull from Fog/Icing Thermodynamics if available
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

    def generate_ai_metar(self, icao: str):
        """Constructs the METAR string based on current engine state."""
        airport = manager.get_airport(icao.upper())
        if airport is None:
            return f"ERROR: Station {icao.upper()} not found in infrastructure database."

        now = telemetry_link.time_manager.get_now()
        time_str = self._format_time_zulu(now)
        env = self._get_environmental_data(airport, now)

        # Build Standard Format
        components = [
            icao.upper(), time_str, "AUTO", 
            env['wind'], env['vis'], env['weather'], 
            env['sky'], env['temp_dew'], env['altimeter'], 
            "RMK AO2 AI_PREDICTED"
        ]
        
        # Filter out empty weather components
        metar_string = " ".join([c for c in components if c])
        return metar_string

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

        # Baseline TAF
        taf_lines = [
            f"TAF {icao.upper()} {time_str} {valid_period} {env['wind']} {env['vis']} {env['weather']} {env['sky']}"
        ]

        # Calculate a future shift using timedelta (e.g., frontal passage in 6 hours)
        shift_time = now + datetime.timedelta(hours=6)
        fm_time = shift_time.strftime("%d%H%M")
        
        # Simulate worsening conditions
        taf_lines.append(
            f"  FM{fm_time} 31020G30KT 2SM -RA OVC015"
        )
        
        return "\n".join(taf_lines)

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

# --- CLI EXECUTION ---
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
