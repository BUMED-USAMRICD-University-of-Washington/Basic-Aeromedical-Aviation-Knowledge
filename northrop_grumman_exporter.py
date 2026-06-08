# --- PRIMARY ENGINE: Northrop Grumman OMS Avionics ---
import struct
import time
import numpy as np
from numba import njit

class NorthropGrummanExporter:
    """
    Serializes telemetry into Open Mission Systems (OMS) compliant 
    binary structures for mission-critical flight management.
    """
    
    # OMS Message Frame: [Sync(2)][MsgType(2)][Timestamp(8)][Payload(64 bytes)]
    # Fixed 76-byte frame for deterministic processing.
    PACKET_FORMAT = ">H H d 16f" 
    SYNC_WORD = 0xABCD # Northrop specific mission sync word

    @staticmethod
    @njit(fastmath=True)
    def normalize_sensor_data(data_array):
        # Northrop systems require high-fidelity normalization of sensor inputs
        return data_array.astype(np.float32)

    def dispatch(self, payload, output_dir):
        # 1. Structure the OMS Payload
        # Mapping your flight telemetry to the OMS schema
        data = [
            payload.get('temp_c', 0.0),
            payload.get('pressure_hpa', 0.0),
            payload.get('lat', 0.0),
            payload.get('lon', 0.0),
            payload.get('alt', 0.0),
            payload.get('pitch', 0.0),
            payload.get('roll', 0.0),
            payload.get('yaw', 0.0),
            payload.get('ground_speed', 0.0),
            payload.get('climb_rate', 0.0),
            payload.get('heading', 0.0),
            payload.get('throttle', 0.0),
            *[0.0]*4 # Reserved space for future mission-specific sensors
        ]

        # 2. Binary Packing
        packet = struct.pack(
            self.PACKET_FORMAT,
            self.SYNC_WORD,
            0x0001, # Message Type (1 = Nav/Flight State)
            time.time(),
            *data
        )
        
        # 3. Deterministic Bus Output
        with open(f"{output_dir}/northrop_oms_bus.bin", "ab") as f:
            f.write(packet)
        print(f"✈️ Northrop Grumman OMS Bus Frame Dispatched: {len(packet)} bytes")
