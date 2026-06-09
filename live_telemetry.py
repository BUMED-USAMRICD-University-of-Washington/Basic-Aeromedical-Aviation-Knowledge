# memory_manager.py
from dynamic_memory_cache import DynamicMemoryCache

# Create one shared cache instance for the whole app
shared_cache = DynamicMemoryCache(percentage=0.25)

# live_telemetry.py
# Interfaces with USB DGPS/RTK and Barometric Elevation Dongles

import os
import time
import sys

# --- HARDWARE ACCELERATION & MATH ENGINES ---
from numba import njit
# live_telemetry.py
# High-Speed, Else-Less NMEA Serial Parser for Universal Navigation

import serial
import time
import pynmea2

# --- CENTRALIZED DATA BUS ---
import telemetry_link

# --- HARDWARE ABSTRACTION LAYER (HAL) ---
try:
    import cupy as xp  # NVIDIA GPU Acceleration
    HAS_GPU = True
    # Note: Serial reads are inherently CPU-bound, but HAL is initialized 
    # here to maintain repository architecture and support future batching.
except ImportError:
    import numpy as xp # CPU Fallback
    HAS_GPU = False

class LiveTelemetryDaemon:
    """
    Else-Less daemon for parsing serial GPS/GNSS data.
    Designed to fail-fast on corrupted serial strings to maintain 0-latency polling.
    """
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600, reference_frame="Earth"):
        self.port = port
        self.baudrate = baudrate
        self.reference_frame = reference_frame
        self.serial_conn = None

    def connect_serial(self):
        """Else-less serial connection logic."""
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"📡 Serial link established on {self.port} at {self.baudrate} baud.")
            return True
        except serial.SerialException as e:
            print(f"⚠️ Serial Connection Failed: {e}")
            return False

    def parse_nmea_sentence(self, line: str):
        """
        Else-less NMEA Serial Parser.
        Drops corrupted or irrelevant strings instantly to free CPU cycles.
        """
        # 🛑 GUARD 1: Ignore irrelevant or empty serial sentences
        if not line.startswith(('$GPGGA', '$GNGGA', '$GPRMC', '$GNRMC')):
            return None

        # 🛑 GUARD 2: Catch serial bus corruption (ParseError)
        try:
            msg = pynmea2.parse(line)
        except pynmea2.ParseError:
            return None

        # 🛑 GUARD 3: Validate satellite fix for GGA sentences (0 = Invalid)
        if hasattr(msg, 'gps_qual') and getattr(msg, 'gps_qual', 0) == 0:
            return None

        # 🛑 GUARD 4: Validate active status for RMC sentences ('V' = Void, 'A' = Active)
        if hasattr(msg, 'status') and getattr(msg, 'status', 'V') != 'A':
            return None

        # ✅ HAPPY PATH: Valid 3D Fix Acquired
        lat = getattr(msg, 'latitude', 0.0)
        lon = getattr(msg, 'longitude', 0.0)
        
        # Safely extract altitude (RMC sentences do not carry altitude)
        alt_m = getattr(msg, 'altitude', 0.0)
        alt_m = alt_m if alt_m is not None else 0.0
        elevation_ft = alt_m * 3.280839895013123
        
        sats = getattr(msg, 'num_sats', 0)
        
        # Enforce 15-decimal precision standard for the flight computer
        return {
            "status": "SUCCESS",
            "reference_frame": self.reference_frame,
            "latitude": round(float(lat), 15),
            "longitude": round(float(lon), 15),
            "elevation_ft": round(float(elevation_ft), 15),
            "satellites_locked": int(sats)
        }

    def run_watchdog_loop(self):
        """Continuous high-speed polling of the serial bus."""
        # 🛑 GUARD 1: Cannot run without a serial connection
        if not self.connect_serial():
            print("🛑 Daemon aborted: No serial device found.")
            return
            
        print(f"🚀 Live Telemetry Daemon Active. Polling {self.reference_frame} NMEA stream...")
        
        while True:
            # 1. Attempt to read the serial bus
            try:
                raw_line = self.serial_conn.readline()
            except serial.SerialException:
                print("⚠️ Serial bus dropped. Attempting reconnect...")
                time.sleep(1.0)
                self.connect_serial()
                continue

            # 🛑 GUARD 2: Empty read (Timeout)
            if not raw_line:
                continue

            # 2. Decode the raw bytes
            try:
                decoded_line = raw_line.decode('ascii', errors='ignore').strip()
            except UnicodeDecodeError:
                continue

            # 3. Parse the data
            parsed_data = self.parse_nmea_sentence(decoded_line)
            
            # 🛑 GUARD 3: Invalid or dropped sentence
            if not parsed_data:
                continue

            # ✅ HAPPY PATH: Push validated, 15-decimal precision data to the Global State
            telemetry_link.update_global_state("navigation", "live_gps", parsed_data)
            telemetry_link.update_global_state("navigation", "planetary_reference_frame", self.reference_frame)


if __name__ == "__main__":
    print("=================================================================")
    print("        UNIVERSAL GPS TELEMETRY DAEMON (ELSE-LESS KERNEL)        ")
    print("=================================================================\n")
    
    # Initialize the Daemon. 
    # Change port to 'COM3' or similar if running on Windows.
    # Change reference_frame to "Mars" or "Luna" if plugged into the Universal mapper.
    daemon = LiveTelemetryDaemon(port='/dev/ttyUSB0', baudrate=9600, reference_frame="Earth")
    
    try:
        daemon.run_watchdog_loop()
    except KeyboardInterrupt:
        print("\n🛑 Telemetry Daemon terminated by operator.")
        if daemon.serial_conn and daemon.serial_conn.is_open:
            daemon.serial_conn.close()
            print("🔒 Serial port closed safely.")
