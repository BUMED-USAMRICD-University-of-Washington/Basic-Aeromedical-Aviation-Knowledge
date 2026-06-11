import json
import os
import numpy as np
import matplotlib.pyplot as plt

class JetAcousticProfiler:
    def __init__(self, jet_name="Default_Jet"):
        self.jet_name = jet_name
        # Profile structure maps: throttle_pct -> {freq, temp, cancellation_eff, thrust_gain}
        self.profile_data = {}

    def log_throttle_point(self, throttle_pct, frequency, temp_k, matrix_results):
        """
        Records an active telemetry snapshot into the running profile memory matrix.
        Called automatically by the flight loops when a throttle shift settles.
        """
        # Round throttle to nearest integer percent to keep discrete map index keys
        key = int(round(throttle_pct))
        
        self.profile_data[str(key)] = {
            "captured_frequency_hz": round(frequency, 2),
            "exhaust_temp_kelvin": round(temp_k, 2),
            "cancellation_efficiency_percent": matrix_results["cancellation_efficiency_percent"],
            "scavenging_thrust_gain_newtons": matrix_results["scavenging_thrust_gain_newtons"]
        }

    def save_profile_to_disk(self, directory="profiles"):
        """Saves the complete mapped acoustic matrix to a JSON file."""
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        filepath = os.path.join(directory, f"{self.jet_name}_acoustic_profile.json")
        payload = {
            "jet_model_identity": self.jet_name,
            "profile_mapping": self.profile_data
        }
        
        with open(filepath, 'w') as f:
            json.dump(payload, f, indent=2)
        print(f"\n[PROFILER] Profile successfully written to disk: {filepath}")

    def load_profile_from_disk(self, filepath):
        """Loads a pre-existing jet profile directly back into active system memory."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.jet_name = data["jet_model_identity"]
        self.profile_data = data["profile_mapping"]
        print(f"[PROFILER] Swapped active jet engine profile to: {self.jet_name}")

    def generate_tuning_graph(self):
        """
        Builds and displays a comprehensive dual-axis evaluation plot mapping 
        Tuning Alignment Efficiency and Thrust Boost across the total throttle bounds.
        """
        if not self.profile_data:
            print("[PROFILER ERROR] Cannot render plot. Active profile memory matrix is empty.")
            return

        # Sort the map keys numerically to ensure lines draw left-to-right correctly
        sorted_keys = sorted([int(k) for k in self.profile_data.keys()])
        
        throttles = []
        frequencies = []
        cancellations = []
        gains = []

        for k in sorted_keys:
            throttles.append(k)
            item = self.profile_data[str(k)]
            frequencies.append(item["captured_frequency_hz"])
            cancellations.append(item["cancellation_efficiency_percent"])
            gains.append(item["scavenging_thrust_gain_newtons"])

        # Construct the plotting figure frame canvas
        fig, ax1 = plt.subplots(figsize=(10, 5))

        # Axis 1: Plot Acoustic Phase Cancellation Efficiency Line
        color = 'tab:blue'
        ax1.set_xlabel('Engine Throttle Command (%)', fontweight='bold')
        ax1.set_ylabel('Cancellation Phase Lock Efficiency (%)', color=color, fontweight='bold')
        ax1.plot(throttles, cancellations, color=color, marker='o', linewidth=2.5, label='Cancellation Lock')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True, linestyle='--', alpha=0.6)

        # Axis 2: Overlay the Kinetic Scavenging Thrust Force Boost Curve
        ax2 = ax1.twinx()
        color = 'tab:red'
        ax2.set_ylabel('Kinetic Thrust Gain Force (Newtons)', color=color, fontweight='bold')
        ax2.plot(throttles, gains, color=color, marker='s', linewidth=2.0, linestyle=':', label='Thrust Gain')
        ax2.tick_params(axis='y', labelcolor=color)

        # Title adjustments matching engineering specifications
        plt.title(f"Acoustic Resonant Tuning Profile Matrix: {self.jet_name}", fontsize=12, fontweight='bold', pad=15)
        fig.tight_layout()
        
        print(f"[PROFILER] Displaying tuning profile window canvas for {self.jet_name}...")
        plt.show()
