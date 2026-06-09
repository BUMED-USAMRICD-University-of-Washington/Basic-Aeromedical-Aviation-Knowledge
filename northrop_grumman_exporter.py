import multiprocessing as mp
import struct
import time
import numba
from numba import njit
@njit(fastmath=True)
try:
    import cupy as xp
    HAS_GPU = True
except ImportError:
    import numpy as xp
    HAS_GPU = False
    print("CPU Fallback: Standard Vectorization Active (Performance)")
class NorthropGrummanExporter:
    """
    Serializes telemetry into Open Mission Systems (OMS) compliant 
    binary structures for mission-critical flight management.
    """
    PACKET_FORMAT = ">H H d 16f" 
    SYNC_WORD = 0xABCD # Northrop specific mission sync word
    @staticmethod
    @njit(fastmath=True)
    def normalize_sensor_data(data_array):
        return data_array.astype(np.float32)
    def dispatch(self, payload, output_dir):
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
        packet = struct.pack(
            self.PACKET_FORMAT,
            self.SYNC_WORD,
            0x0001, # Message Type (1 = Nav/Flight State)
            time.time(),
            *data
        )
        with open(f"{output_dir}/northrop_oms_bus.bin", "ab") as f:
            f.write(packet)
        print(f"Northrop Grumman OMS Bus Frame Dispatched: {len(packet)} bytes")
