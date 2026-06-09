import struct
import time
import numpy as np
from numba import njit
import multiprocessing as mp
try:
    import cupy as xp
    HAS_GPU = True
except ImportError:
    import numpy as xp
    HAS_GPU = False
class LockheedTelemetryExporter:
    """
    Serializes flight data into MIL-STD-1553B binary bus structures.
    Uses Numba-accelerated fixed-point conversion for deterministic timing.
    """
    PACKET_FORMAT = ">HHH16H"
    SYNC_WORD = 0x8000
    def __init__(self):
        self.pool = mp.Pool(processes=mp.cpu_count())
    @staticmethod
    @njit(fastmath=True)
    def fast_convert_to_fixed_point(data_array, scale_factor=1000.0):
        """
        Numba-accelerated conversion of floating point telemetry 
        to 16-bit integer words for deterministic bus transfer.
        """
        output = np.zeros(len(data_array), dtype=np.uint16)
        for i in range(len(data_array)):
            val = int(data_array[i] * scale_factor)
            output[i] = val & 0xFFFF # Mask to 16-bit
        return output
    def pack_mil_std_1553(self, payload):
        """
        Dispatches telemetry into a rigid binary 1553B data bus structure.
        """
        stream = np.array([
            payload.get('temp_c', 0.0),
            payload.get('pressure_hpa', 0.0),
            payload.get('lat', 0.0),
            payload.get('lon', 0.0),
            payload.get('alt', 0.0),
            payload.get('pitch', 0.0),
            payload.get('roll', 0.0),
            payload.get('yaw', 0.0),
            *[0.0]*8 # Remaining slots in the 16-word buffer
        ], dtype=np.float64)
        fixed_point_words = self.fast_convert_to_fixed_point(stream)
        packet = struct.pack(
            self.PACKET_FORMAT,
            self.SYNC_WORD,
            0x0001,
            len(fixed_point_words),
            *fixed_point_words
        )
        return packet
    def dispatch(self, payload, output_dir="logs"):
        """
        Exports the payload as a Lockheed-standard binary bus dump.
        """
        binary_blob = self.pack_mil_std_1553(payload)
        
        filename = f"{output_dir}/lockheed_bus_dump.bin"
        with open(filename, "ab") as f:
            f.write(binary_blob)
        print(f"Lockheed Martin Binary Bus Dump Appended: {len(binary_blob)} bytes")
if __name__ == "__main__":
    exporter = LockheedTelemetryExporter()

    test_payload = {
        "temp_c": 15.5, 
        "pressure_hpa": 1013.2, 
        "lat": 47.4480, 
        "lon": -122.3088, 
        "alt": 3000.0,
        "pitch": 5.0,
        "roll": 0.0,
        "yaw": 180.0
    }
    exporter.dispatch(test_payload)
