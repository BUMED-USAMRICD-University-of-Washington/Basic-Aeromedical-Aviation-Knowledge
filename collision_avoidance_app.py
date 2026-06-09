import streamlit as str
import numpy as np
import requests
import time
from scipy.stats import norm
# Import your isolated intent module
from intent_engine import IntruderIntentAnalyst

# --- STAGE 1: SET UP USER INTERFACE ---
str.set_page_config(page_title="ACAS X / ADS-B Collision Engine", layout="wide")
str.title("🛩️ NextGen Automated Cooperative Collision Avoidance Engine")

# Sidebar Configuration for ADS-B Exchange API
str.sidebar.header("API & Hardware Configuration")
adsb_api_key = str.sidebar.text_input("ADS-B Exchange API Key", type="password")
ownship_icao = str.sidebar.text_input("Ownship Mode S Hex (ICAO)", value="A1B2C3")
scan_radius_nm = str.sidebar.slider("Scan Boundary (Nautical Miles)", 1.0, 10.0, 5.0)

# Physical Constants & Global Safety Puck Geometry
G_ACCEL = 9.81         # m/s^2
NM_TO_METERS = 1852    # 1 NM = 1852 meters
FT_TO_METERS = 0.3048  # 1 FT = 0.3048 meters
PUCK_R = 500 * FT_TO_METERS  # 500 ft Horizontal Radius
PUCK_H = 100 * FT_TO_METERS  # 100 ft Vertical Buffer Height

# --- STAGE 2: KINEMATICS & IMM KALMAN FILTER ENGINES ---
class IMMKalmanFilter:
    """
    An Interacting Multiple Model Tracker tracking two parallel profiles:
    Model 1: Constant Velocity (CV) - Straight and Level flight
    Model 2: Coordinated Turn (CT) - Aggressive banking maneuvers
    """
    def __init__(self, dt=1.0):
        self.dt = dt
        self.mu = np.array([0.8, 0.2])  # Initialized at [CV: 80%, CT: 20%]
        self.p_ij = np.array([[0.95, 0.05],
                              [0.05, 0.95]])
        
        self.x_cv = np.zeros((6, 1))
        self.x_ct = np.zeros((6, 1))
        
        self.P_cv = np.eye(6) * 10.0
        self.P_ct = np.eye(6) * 10.0
        
        self.H = np.array([[1, 0, 0, 0, 0, 0],
,
                           [0, 0, 0, 0, 1, 0]])
        
        self.R = np.diag([25.0**2, 25.0**2, 5.0**2]) # GPS Noise Variance in meters

    def predict_and_update(self, z_meas, omega=0.05):
        # 1. Mix State Estimations
        c_bar = self.p_ij.T @ self.mu
        omega_ij = (self.p_ij * self.mu[:, None]) / c_bar
        
        x_0cv = omega_ij[0,0]*self.x_cv + omega_ij[1,0]*self.x_ct
        x_0ct = omega_ij[0,1]*self.x_cv + omega_ij[1,1]*self.x_ct
        
        # 2. Linear/Non-Linear Transition Models (F Matrix)
        F_cv = np.array([[1, 0, self.dt, 0, 0, 0],
                         [0, 1, 0, self.dt, 0, 0],
,
 ,
                         [0, 0, 0, 0, 1, self.dt],
                         [0, 0, 0, 0, 0, 1]])
        
        sin_w = np.sin(omega * self.dt) / (omega if omega != 0 else 1e-5)
        cos_w = (1 - np.cos(omega * self.dt)) / (omega if omega != 0 else 1e-5)
        F_ct = np.array([[1, 0, sin_w, -cos_w, 0, 0],
                         [0, 1, cos_w, sin_w, 0, 0],
                         [0, 0, np.cos(omega*self.dt), -np.sin(omega*self.dt), 0, 0],
                         [0, 0, np.sin(omega*self.dt), np.cos(omega*self.dt), 0, 0],
                         [0, 0, 0, 0, 1, self.dt],
                         [0, 0, 0, 0, 0, 1]])

        Q = np.eye(6) * 2.0
        
        self.x_cv = F_cv @ x_0cv
        self.x_ct = F_ct @ x_0ct
        self.P_cv = F_cv @ self.P_cv @ F_cv.T + Q
        self.P_ct = F_ct @ self.P_ct @ F_ct.T + Q
        
        # 3. Apply Extended Kalman Update Steps
        y_cv = z_meas - (self.H @ self.x_cv)
        y_ct = z_meas - (self.H @ self.x_ct)
        
        S_cv = self.H @ self.P_cv @ self.H.T + self.R
        S_ct = self.H @ self.P_ct @ self.H.T + self.R
        
        K_cv = self.P_cv @ self.H.T @ np.linalg.inv(S_cv)
        K_ct = self.P_ct @ self.H.T @ np.linalg.inv(S_ct)
        
        self.x_cv += K_cv @ y_cv
        self.x_ct += K_ct @ y_ct
        self.P_cv = (np.eye(6) - K_cv @ self.H) @ self.P_cv
        self.P_ct = (np.eye(6) - K_ct @ self.H) @ self.P_ct
        
        # 4. Re-evaluate Model Likelihood
        like_cv = max(1e-10, norm.pdf(y_cv[0,0], 0, np.sqrt(S_cv[0,0])) * norm.pdf(y_cv[1,0], 0, np.sqrt(S_cv[1,1])))
        like_ct = max(1e-10, norm.pdf(y_ct[0,0], 0, np.sqrt(S_ct[0,0])) * norm.pdf(y_ct[1,0], 0, np.sqrt(S_ct[1,1])))
        
        raw_mu = np.array([like_cv * c_bar[0], like_ct * c_bar[1]])
        self.mu = raw_mu / np.sum(raw_mu)
        
        return self.mu[0] * self.x_cv + self.mu[1] * self.x_ct

# --- STAGE 3: COOPERATIVE RESOLUTION & ENERGETIC DECISION LOGIC ---
def calculate_modified_tau(x, y, vx, vy):
    r = np.sqrt(x**2 + y**2)
    r_dot = (x*vx + y*vy) / (r if r != 0 else 1e-5)
    dmod = 0.5 * NM_TO_METERS  # 0.5 NM Safety Buffer Pad
    if r_dot >= 0: return float('inf')
    return -(r**2 - dmod**2) / (r * r_dot)

def evaluate_cooperative_bellman_resolution(rel_x, rel_y, rel_vx, rel_vy, rel_h, rel_vh, intruder_intent):
    """ Cooperative MDP Engine: Resolves conflicts adaptively based on identified intent """
    tau_mod = calculate_modified_tau(rel_x, rel_y, rel_vx, rel_vy)
    
    # Check if target breaches core physical safety bubble
    if abs(rel_h) < PUCK_H and np.sqrt(rel_x**2 + rel_y**2) < PUCK_R:
        if intruder_intent == "AGGRESSIVE_DIVE":
            return "🔺 CRITICAL COOPERATIVE OVERRIDE: PULL UP / CLIMB MAX POWER"
        elif intruder_intent == "AGGRESSIVE_CLIMB":
            return "🔻 CRITICAL COOPERATIVE OVERRIDE: PUSH DOWN / DESCEND IMMEDIATELY"
        return "⚠️ EMERGENCY: EXECUTE HARD MULTI-AXIS ESCAPE"
        
    # Tactical Warning Envelope (Tau < 25 seconds)
    if tau_mod < 25.0:
        if intruder_intent == "BANKING_RIGHT":
            return "🔄 COOPERATIVE MATCH: TURN RIGHT (Left-to-Left Passing Geometry Confirmed)"
            
        elif intruder_intent == "BANKING_LEFT":
            # The Mirror Trap: Intruder turned left into our path. Clear out into vertical space.
            if rel_h >= 0:
                return "🔺 BLUNDER/MIRROR DETECTED: ABANDON TURN -> EXECUTE EMERGENCY CLIMB"
            else:
                return "🔻 BLUNDER/MIRROR DETECTED: ABANDON TURN -> EXECUTE EMERGENCY DESCENT"
                
        elif intruder_intent == "AGGRESSIVE_CLIMB":
            return "📉 COOPERATIVE VERTICAL SPLIT: DESCEND, DESCEND (-1,500 ft/min)"
        elif intruder_intent == "AGGRESSIVE_DIVE":
            return "📈 COOPERATIVE VERTICAL SPLIT: CLIMB, CLIMB (+1,500 ft/min)"
            
        if rel_vh <= 0:
            return "📈 AUTOMATED ADVISORY: CLIMB, CLIMB"
        else:
            return "📉 AUTOMATED ADVISORY: DESCEND, DESCEND"
            
    elif tau_mod < 40.0:
        return f"🟡 REMAIN WELL CLEAR: Target diagnosed as [{intruder_intent}]"
        
    return "✅ PATH CLEAR: Normal Trajectory Operations"

# --- STAGE 4: RUNTIME RECONGNITION LAYER & DATA LOOP ---
if not adsb_api_key:
    str.warning("Please enter your ADS-B Exchange API Key in the sidebar to run live tracking.")
else:
    placeholder = str.empty()
    tracker = IMMKalmanFilter(dt=1.0)
    # Instantiate the isolated modular analyst class to manage history tracking
    intent_analyst = IntruderIntentAnalyst(dt=1.0)
    
    sim_t = 0
    while True:
        sim_t += 1
        
        # Live Production Hook
        url = f"https://adsbexchange.com{ownship_icao}/radius/{scan_radius_nm}"
        headers = {"api-auth": adsb_api_key}
        
        try:
            # --- SIMULATING API DATA INPUTS (Mirroring ADS-B Exchange JSON) ---
            # Once your API token is live, uncomment the lines below:
            # response = requests.get(url, headers=headers)
            # data = response.json()
            # ac_list = data.get("ac", [])
            
            ac_list = [
                {
                    "hex": ownship_icao.lower(),  # Your Ownship Target data footprint
                    "lat": 47.6062, "lon": -122.3321, "alt_baro": 5000, 
                    "gs": 120, "track": 360, "baro_rate": 0
                },
                {
                    "hex": "b4c5d6",  # Intruder blundering into your path via a left-hand turn
                    "lat": 47.6065, "lon": -122.3321, "alt_baro": 4980, 
                    "gs": 180, "track": 180 - (sim_t * 6), "baro_rate": -120
                }
            ]
            # -----------------------------------------------------------------

            # STEP 1: Parse data array specifically to isolate your ownship vectors
            ownship_data = None
            for ac in ac_list:
                if ac.get("hex", "").strip().lower() == ownship_icao.strip().lower():
                    ownship_data = ac
                    break
            
            if ownship_data is None:
                str.sidebar.error(f"Aircraft Hex {ownship_icao} not captured in receiver footprint.")
                own_x, own_y, own_h = 0.0, 0.0, 5000 * FT_TO_METERS
                own_vx, own_vy, own_vh = 0.0, 0.0, 0.0
            else:
                own_h = ownship_data.get("alt_baro", 0) * FT_TO_METERS
                own_vh = ownship_data.get("baro_rate", 0) * (FT_TO_METERS / 60.0)
                gs_mps = ownship_data.get("gs", 0) * 0.514444
                track_rad = np.radians(ownship_data.get("track", 0))
                own_vx = gs_mps * np.sin(track_rad)
                own_vy = gs_mps * np.cos(track_rad)
                own_x, own_y = 0.0, 0.0 

            # STEP 2: Loop through intruders while strictly EXCLUDING your own hex identifier
            for intruder in ac_list:
                intruder_hex = intruder.get("hex", "").strip().lower()
                
                # THE FILTER HOOK
                if intruder_hex == ownship_icao.strip().lower():
                    continue
                
                # Fetch telemetry for the threat aircraft
                int_gs = intruder.get("gs", 0)
                int_track = intruder.get("track", 0)
int_baro_rate = intruder.get("baro_rate", 0)
# CALL THE ISOLATED INTENT MODULE FOR DIAGNOSIS
predicted_intent, lat_g, vert_g = intent_analyst.diagnose_behavior_profile(
intruder_hex, int_gs, int_track, int_baro_rate
)
# Coordinate calculations for tracking matrix
int_h = intruder.get("alt_baro", 0) * FT_TO_METERS
int_vh = int_baro_rate * (FT_TO_METERS / 60.0)
int_gs_mps = int_gs * 0.514444
int_track_rad = np.radians(int_track)
int_vx = int_gs_mps * np.sin(int_track_rad)
int_vy = int_gs_mps * np.cos(int_track_rad)
# Geocentric distance simulation transformation offsets
rel_raw_x = 450.0 - (sim_t * 15) # Closing speed dynamics
rel_raw_y = 180.0
rel_raw_h = int_h - own_h
rel_vx_delta = int_vx - own_vx
rel_vy_delta = int_vy - own_vy
rel_vh_delta = int_vh - own_vh
# Smooth out sensor telemetry noise with the IMM filter
z_meas = np.array([[rel_raw_x], [rel_raw_y], [rel_raw_h]])
smoothed_state = tracker.predict_and_update(z_meas, omega=0.02)
s_x, s_y, _, _, s_h, _ = smoothed_state.flatten()
# Run the cooperative matrix solver to get safety commands
tau_val = calculate_modified_tau(s_x, s_y, rel_vx_delta, rel_vy_delta)
resolution = evaluate_cooperative_bellman_resolution(
s_x, s_y, rel_vx_delta, rel_vy_delta, s_h, rel_vh_delta, predicted_intent
)
# Render parameters dynamically onto Streamlit window dashboards
with placeholder.container():
str.subheader(f"Monitoring Airspace Threat Matrix: [Target Hex: {intruder_hex.upper()}]")
str.info(f"📋 AI Diagnostic Assessment: Target is currently [{predicted_intent}] (Lat-g: {lat_g:.2f}g | Vert-g: {vert_g:.2f}g)")
col1, col2, col3 = str.columns(3)
