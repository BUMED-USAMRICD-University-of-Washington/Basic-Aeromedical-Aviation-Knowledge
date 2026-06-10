"""
Acoustic Wave Resonant Tuning Engine
Integrates background microphone tracking, high-fidelity aerospace plume matrices,
and real-time JSON serialization for active node tuning across varying engine formats.
Optimized specifically for simultaneous Max Power Output and Noise Cancellation.
"""

import threading
import time
import json
import datetime
import numpy as np
import pyaudio

# =====================================================================
# MODULE 1: ASYNCHRONOUS MICROPHONE ACOUSTIC CAPTURE SYSTEM
# =====================================================================
class AsyncAcousticTuner(threading.Thread):
    def __init__(self, sample_rate=44100, chunk_size=4096, noise_floor=0.005):
        super().__init__()
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.noise_floor = noise_floor
        
        self.running = False
        self._lock = threading.Lock()
        self.latest_frequency = 0.0
        
        self.p = None
        self.stream = None

    def run(self):
        self.p = pyaudio.PyAudio()
        try:
            self.stream = self.p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
        except Exception as e:
            print(f"\n[FATAL] Thread failed to mount audio hardware interface: {e}")
            return

        self.running = True

        while self.running:
            try:
                raw_data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                audio_data = np.frombuffer(raw_data, dtype=np.float32)
                
                # Apply Hann window to mitigate spectral edge leakage
                windowed_audio = audio_data * np.hanning(len(audio_data))
                
                # Calculate Root-Mean-Square amplitude to test noise floor limits
                rms_amplitude = np.sqrt(np.mean(windowed_audio**2))
                if rms_amplitude < self.noise_floor:
                    current_freq = 0.0
                else:
                    # Execute Fast Fourier Transform to analyze spatial frequency buckets
                    fft_magnitude = np.abs(np.fft.rfft(windowed_audio))
                    frequencies = np.fft.rfftfreq(self.chunk_size, d=1.0 / self.sample_rate)
                    
                    # Exclude subsonic room rumblings under 20Hz
                    valid_idx = np.where(frequencies > 20.0)
                    if len(valid_idx) > 0:
                        peak_idx = np.argmax(fft_magnitude[valid_idx])
                        current_freq = frequencies[valid_idx][peak_idx]
                    else:
                        current_freq = 0.0
                
                with self._lock:
                    self.latest_frequency = current_freq

            except Exception:
                pass
            
            time.sleep(0.001)

        self._cleanup()

    def get_frequency(self):
        with self._lock:
            return self.latest_frequency

    def stop(self):
        self.running = False

    def _cleanup(self):
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
        if self.p:
            self.p.terminate()

# =====================================================================
# MODULE 2: HIGH-FIDELITY MAX POWER ACOUSTIC MATRIX
# =====================================================================
class MaxPowerAcousticMatrix:
    def __init__(self, fixed_length=2.45, nozzle_radius=0.435, gas_constant=291.4, gamma=1.334):
        """
        Initializes the mechanical boundary parameters of the aircraft engine core.
        """
        self.L_physical = fixed_length
        self.r = nozzle_radius
        self.R = gas_constant
        self.gamma = gamma
        self.end_correction = 0.6 * self.r
        
        # Nominal baseline thrust force for scaling metrics (e.g., F135 engine class)
        self.nominal_thrust_newtons = 130000.0 

    def evaluate_max_power_tuning(self, live_frequency, exhaust_temp_k):
        """
        Calculates fluid dynamics parameters to balance destructive acoustic 
        interference (noise cancellation) and kinetic thrust optimization.
        """
        if live_frequency <= 0:
            return {
                "c_plume": 0.0, "l_target": 0.0, "error_m": 0.0, 
                "helmholtz": 0.0, "cancellation_efficiency_percent": 0.0,
                "scavenging_thrust_gain_newtons": 0.0
            }

        # 1. Dynamic Speed of Sound calculation inside superheated gas environment
        c_plume = np.sqrt(self.gamma * self.R * exhaust_temp_k)
        
        # 2. Locate exact quarter-wave node point (Optimal Cancellation Target)
        l_effective_target = c_plume / (4.0 * live_frequency)
        l_physical_target = l_effective_target - self.end_correction
        
        # 3. Calculate alignment displacement error vector
        node_error_meters = l_physical_target - self.L_physical
        abs_error = abs(node_error_meters)
        
        # 4. Nondimensional Helmholtz calculation validation
        omega = 2.0 * np.pi * live_frequency
        helmholtz_number = (omega * self.L_physical) / c_plume
        
        # 5. Calculate Phase Cancellation Efficiency Profile (Bell-curve tracking)
        # Closer the error is to 0.0 meters, the closer cancellation matches 100%
        cancellation_efficiency = np.exp(-5.0 * (abs_error ** 2))
        
        # 6. Kinetic Scavenging Power Gain Calculation
        # Destructive wave reflection eliminates local exhaust backpressure restrictions.
        # Max performance gains (~3.5% kinetic volumetric efficiency leap) occur at 100% cancellation.
        max_gain_coefficient = 0.035 
        thrust_gain_factor = max_gain_coefficient * cancellation_efficiency
        scavenging_thrust_gain_n = self.nominal_thrust_newtons * thrust_gain_factor
        
        return {
            "c_plume": c_plume,
            "l_target": l_physical_target,
            "error_m": node_error_meters,
            "helmholtz": helmholtz_number,
            "cancellation_efficiency_percent": round(cancellation_efficiency * 100, 2),
            "scavenging_thrust_gain_newtons": round(scavenging_thrust_gain_n, 1)
        }

# =====================================================================
# MODULE 3: CENTRAL FLIGHT INTEGRATION LOGIC & RUNNER LOOP
# =====================================================================
def run_telemetry_simulation():
    # Load default configuration geometry (e.g., F-35A / F135-PW-100 baseline setup)
    engine_analyzer = MaxPowerAcousticMatrix(
        fixed_length=2.450, 
        nozzle_radius=0.435, 
        gas_constant=291.40, 
        gamma=1.334
    )
    
    # Initialize and fire up background mic audio listeners
    audio_thread = AsyncAcousticTuner()
    audio_thread.daemon = True
    audio_thread.start()
    
    print("=" * 75)
    print("      AEROSPACE MAX-POWER STANDING WAVE TUNING MATRIX ONBOARD")
    print("          Status: Active | Maximizing Volumetric Scavenging Force")
    print("=" * 75)
    print("[MAIN] Background tracking running. Press Ctrl+C to terminate application gracefully.\n")
    
    frame_id = 0
    
    try:
        while True:
            frame_id += 1
            
            # Fetch simulated current core parameters from aircraft metrics
            simulated_rpm = 13450.0 + (np.sin(frame_id * 0.1) * 150.0)
            simulated_temp_k = 1050.0 + (np.cos(frame_id * 0.05) * 25.0)
            
            # Read real-time frequency from the background audio processor
            live_tone_hz = audio_thread.get_frequency()
            
            # Run the analytical gas dynamics node solver
            metrics = engine_analyzer.evaluate_max_power_tuning(live_tone_hz, simulated_temp_k)
            
            # Compute a proportional thermodynamic modulation correction command
            # Negative feedback forces the temperature shifts required to lock the node
            recommended_temp_delta = -50.0 * metrics["error_m"]
            
            # Determine alignment state descriptive string
            if live_tone_hz <= 0:
                cancellation_status = "awaiting_ignition"
                thrust_state = "STABLE_IDLE"
            elif metrics["cancellation_efficiency_percent"] > 95.0:
                cancellation_status = "optimal_phase_lock"
                thrust_state = "MAX_POWER_EFFICIENCY"
            else:
                cancellation_status = "tuning_out_of_phase"
                thrust_state = "THERMAL_MODULATION_ACTIVE"

            # Build and serialize the comprehensive telemetry payload
            telemetry_packet = {
                "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
                "frame_id": frame_id,
                "engine_state": {
                    "core_rpm": round(simulated_rpm, 1),
                    "exhaust_gas_temperature_kelvin": round(simulated_temp_k, 2)
                },
                "acoustic_listener_stream": {
                    "microphone_status": "active" if live_tone_hz > 0 else "listening_below_noise_floor",
                    "captured_motor_frequency_hz": round(live_tone_hz, 2)
                },
                "acoustic_tuning_matrix": {
                    "computed_speed_of_sound_m_s": round(metrics["c_plume"], 2),
                    "target_physical_length_meters": round(max(0.0, metrics["l_target"]), 4),
                    "current_helmholtz_number": round(metrics["helmholtz"], 4),
                    "node_alignment_error_meters": round(metrics["error_m"], 4)
                },
                "max_power_performance_metrics": {
                    "noise_cancellation_status": cancellation_status,
