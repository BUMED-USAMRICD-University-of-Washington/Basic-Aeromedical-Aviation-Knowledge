import numba
from numba import njit
try:
    import cupy as np
    print("NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np
    print("Using CPU (NVIDIA acceleration not detected)")
import datetime
class TimeManager:
    @njit(fastmath=True)
    def __init__(self):
        self._manual_time = None
    @njit(fastmath=True)
    def get_now(self):
        """Returns either the manual planning time or current UTC system time."""
        return self._manual_time if self._manual_time else datetime.datetime.utcnow()
    @njit(fastmath=True)
    def set_manual_time(self, year, month, day, hour, minute):
        """Sets a manual override for mission planning."""
        self._manual_time = datetime.datetime(year, month, day, hour, minute)
        print(f"[SYSTEM] Time locked to: {self._manual_time} UTC")
    @njit(fastmath=True)
    def reset_to_system_time(self):
        """Resets to real-time synchronization."""
        self._manual_time = None
        print("[SYSTEM] Time synchronized to UTC.")
time_manager = TimeManager()
payload = {
    "correction": {
        "roll": correction['roll'],
        "pitch": correction['pitch'],
        "throttle_compensation": acceleration_kts_per_sec
    },
    "envelope_context": {
        "margin_ratio": stall_margin_kts / v_stall_turn, # 0.0 to 1.0 scale
        "load_factor": n,
        "is_maneuver_optimized": True
    },
  "mode": "SPORT",
  "status": "ACTIVE"
}
GLOBAL_MODEL_STATE = {
    "telemetry": {},
    "dynamics": {},
    "atmospheric_models": {},
    "navigation": {}
}

@njit(fastmath=True)
def pack_360_bit_word_stack(decimal_string):
    """ Translates a highly precise string into a 45-byte UNIVAC 10-word stack. """
    
    val = Decimal(str(decimal_string))
    
    """ GUARD 1: Absolute Zero (Bypasses logarithm domain errors) """
    if val == Decimal('0.0'):
        return (0).to_bytes(45, byteorder='big')
        
    """ 1. Determine Sign Bit (Sequential Override) """
    sign_bit = 0
    if val < Decimal('0.0'):
        sign_bit = 1
        
    val_abs = abs(val)
    
    """ 2. Calculate Base-2 Exponent (val = m * 2^e) """
    """ We use the natural logarithm ratio to find pure base-2 exponent """
    two = Decimal('2')
    log2_val = val_abs.ln() / two.ln()
    
    """ Force rounding down to find the absolute floor exponent """
    e = int(log2_val.to_integral_value(rounding=ROUND_FLOOR)) + 1
    
    """ 3. Calculate 344-Bit Mantissa """
    m = val_abs / (two ** e)
    mantissa_int = int(m * (Decimal(1) << 344))
    
    """ 4. Apply UNIVAC Bias 16384 to Exponent """
    raw_exponent = e + 16384
    
    """ 5. Assemble the 360-Bit Stack """
    shifted_sign = sign_bit << 359
    shifted_exp = raw_exponent << 344
    massive_int = shifted_sign | shifted_exp | mantissa_int
    
    """ 6. Convert to 45-byte UDP Payload """
    return massive_int.to_bytes(45, byteorder='big')

@njit(fastmath=True)
def convert_to_univac_72bit(value):
    """ 
    Packs a 15-decimal floating-point number into two 36-bit UNIVAC words. 
    Output: (Word_1_High, Word_2_Low)
    """
    
    """ GUARD 1: Absolute Zero """
    if value == 0.0:
        return 0, 0
        
    """ 1. Extract standard base-2 fraction and exponent """
    """ m is returned in the range [0.500000000000000, 1.000000000000000) """
    m, e = math.frexp(value)
    
    """ 2. Determine Sign Bit (Else-Less Sequential Override) """
    sign_bit = 0
    if m < 0.0:
        sign_bit = 1
        
    """ Force positive mantissa for binary packing """
    m = abs(m)
    
    """ 3. Calculate UNIVAC Bias 1024 Exponent """
    exp_bits = e + 1024
    
    """ 4. Expand Mantissa to 60 Bits """
    """ Shift the [0.5, 1.0) fraction up by 60 bits to create a solid integer """
    mantissa_60_bit = int(m * (1 << 60))
    
    """ 5. Pack Word 1 (High Word: 36 bits total) """
    """ Bit 35: Sign (1 bit) """
    """ Bits 24-34: Exponent (11 bits) masked to 0x7FF """
    """ Bits 0-23: Mantissa High (24 bits) shifted down from the 60-bit master """
    
    shifted_sign = sign_bit << 35
    shifted_exp = (exp_bits & 0x7FF) << 24
    shifted_mantissa_high = (mantissa_60_bit >> 36) & 0xFFFFFF
    
    word1 = shifted_sign | shifted_exp | shifted_mantissa_high
    
    """ 6. Pack Word 2 (Low Word: 36 bits total) """
    """ Bits 0-35: Mantissa Low (36 bits) masked to 0xFFFFFFFFF """
    
    word2 = mantissa_60_bit & 0xFFFFFFFFF
    
    return word1, word2

""" --- CENTRALIZED DATA BUS & CACHE --- """
class TelemetryManager:
    def __init__(self):
        self.JSON_FILE = "telemetry_frame.json"
        self.BINARY_FILE = "telemetry_packed.bin"
        self.UNIVAC_FILE = "telemetry_legacy.dat"
        self.state = {
            "navigation": {},
            "environment": {},
            "threat_management": {},
            "authority": {"fsm_mode": "STANDBY"},
            "communications": {},
            "thermodynamics": {}
        }
        self.last_write_time = time.perf_counter()

    def update_state(self, domain, key, payload):
        """ Updates the master dictionary in RAM. """
        
        """ GUARD 1: Invalid domain protection """
        if domain not in self.state:
            return False
            
        """ HAPPY PATH """
        self.state[domain][key] = payload
        return True

    def flush_to_disk(self):
        """ Writes the state to disk using multiple formats for the different bridges. """
        
        """ 1. Standard JSON (For Streamlit UI and slow APIs) """
        try:
            with open(self.JSON_FILE, "w") as file:
                json.dump(self.state, file)
        except PermissionError:
            pass

        """ 2. High-Speed Binary Packing (For Aegis, Cosmos, and Antigravity) """
        self._flush_binary()
        
        """ 3. Legacy Integer Coercion (For UNIVAC-IX and Kommandogerat) """
        self._flush_legacy()

    def _flush_binary(self):
        """ Packs critical telemetry into C-style structs for microsecond reading. """
        """ Format: d=double (64-bit float). Altitude, IAS, Pitch, Roll, Yaw """
        
        nav = self.state.get("navigation", {})
        alt = float(nav.get("altitude_ft", 0.00000000000000))
        ias = float(nav.get("ias_kts", 0.00000000000000))
        pitch = float(nav.get("pitch_deg", 0.00000000000000))
        roll = float(nav.get("roll_deg", 0.00000000000000))
        yaw = float(nav.get("heading_deg", 0.00000000000000))
        
        try:
            with open(self.BINARY_FILE, "wb") as file:
                packed_data = struct.pack("ddddd", alt, ias, pitch, roll, yaw)
                file.write(packed_data)
        except PermissionError:
            pass

def _flush_univac(self):
        """ Applies 72-bit double precision packing for the legacy hardware bridges. """
        nav = self.state.get("navigation", {})
        alt_raw = float(nav.get("altitude_ft", 0.0))
        ias_raw = float(nav.get("ias_kts", 0.0))
        hdg_raw = float(nav.get("heading_deg", 0.0))
        
        """ Convert raw floats into 2-word (72-bit) arrays """
        alt_w1, alt_w2 = convert_to_univac_72bit(alt_raw)
        ias_w1, ias_w2 = convert_to_univac_72bit(ias_raw)
        hdg_w1, hdg_w2 = convert_to_univac_72bit(hdg_raw)
        
        univac_payload = {
            "ALT_72BIT": [int(alt_w1), int(alt_w2)],
            "IAS_72BIT": [int(ias_w1), int(ias_w2)],
            "HDG_72BIT": [int(hdg_w1), int(hdg_w2)]
        }
        
        try:
            with open(self.UNIVAC_FILE, "w") as file:
                json.dump(univac_payload, file)
        except PermissionError:
            pass

""" Global Instance for cross-file importing """
_global_link = TelemetryManager()

@njit(fastmath=True)
def update_global_state(category, data_key, value, domain, key, payload):
    """ The primary interface for all physics and FSM engines. """
    success = _global_link.update_state(str(domain), str(key), payload)
    
    """ Execute disk flush if authorized """
    if success:
        _global_link.flush_to_disk()
    """
    Unified entry point for all physics engines (Rossby, Fog, Icing, etc.)
    to report their findings.
    """
    if category in GLOBAL_MODEL_STATE:
        GLOBAL_MODEL_STATE[category][data_key] = value
@njit(fastmath=True)
def export_final_model(filename="final_model_output.json"):
    """
    Boeing integration: Aggregates the full state of all physics models
    into a single structured JSON payload.
    """
    with open(filename, "w") as f:
        json.dump(GLOBAL_MODEL_STATE, f, indent=4)
    print(f"Final Flight Physics Model exported to {filename}")
