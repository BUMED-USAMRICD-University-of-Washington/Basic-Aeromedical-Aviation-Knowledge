# live_telemetry.py
# Interfaces with USB DGPS/RTK and Barometric Elevation Dongles

import serial
import pynmea2
import time
import os

def get_live_position(telemetry_override=None, com_port="/dev/ttyUSB0", baudrate=9600):
    """
    Optimized for Pydroid/Android. Uses an aggressive timeout and 
    checks for device presence before attempting to stream data.
    """
    # Android/Pydroid specific: Verify device path exists
    if not os.path.exists(com_port):
        return {"status": "ERROR", "message": f"Dongle not found at {com_port}. Ensure OTG adapter is connected."}
        
    try:
        with serial.Serial(com_port, baudrate, timeout=2.0) as ser:
            # Clear buffer to avoid stale data during rapid reconnection
            ser.reset_input_buffer()
            
            # Look for GPGGA or GNGGA (Multi-GNSS) sentences
            for _ in range(30): 
                try:
                    line = ser.readline().decode('ascii', errors='replace').strip()
                    if line.startswith(('$GPGGA', '$GNGGA')):
                        msg = pynmea2.parse(line)
                        
                        # Verify we have a valid fix (msg.gps_qual > 0)
                        if msg.gps_qual > 0:
                            elevation_ft = msg.altitude * 3.28084 if msg.altitude else 0.0
                            return {
                                "status": "SUCCESS",
                                "latitude": msg.latitude,
                                "longitude": msg.longitude,
                                "elevation_ft": round(elevation_ft, 2),
                                "satellites_locked": msg.num_sats
                            }
                except pynmea2.ParseError:
                    continue
                    
        return {"status": "ERROR", "message": "Dongle connected, but no satellite fix acquired."}
        
    except Exception as e:
        return {"status": "ERROR", "message": f"Serial error: {str(e)}"}
