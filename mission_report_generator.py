# mission_report_generator.py
import pandas as pd
import numpy as np

class MissionReportGenerator:
    """
    Consolidates exported flight data from PID guidance 
    and atmospheric entry phases into a tactical PDF/Report format.
    """
    def __init__(self, log_path="logs/optimized_3d_pid_trajectory.csv"):
        self.log_path = log_path

    def generate_tactical_summary(self):
        df = pd.read_csv(self.log_path)
        
        # Calculate Mission Critical KPIs
        peak_g = df['Acceleration_g'].max()
        peak_heat = df['HeatFlux_W_cm2'].max()
        final_drift = df['CrossrangeDrift_km'].iloc[-1]
        
        summary = {
            "Mission_Status": "SUCCESS" if abs(final_drift) < 0.5 else "RECALIBRATE",
            "Peak_Load_Gs": round(peak_g, 2),
            "Peak_Thermal_Load_Wcm2": round(peak_heat, 2),
            "Final_Lateral_Offset_m": round(final_drift * 1000, 2)
        }
        return summary

# Integration into telemetry loop:
# Once export_telemetry.py finishes the dispatch, 
# you call this to verify performance against requirements.
