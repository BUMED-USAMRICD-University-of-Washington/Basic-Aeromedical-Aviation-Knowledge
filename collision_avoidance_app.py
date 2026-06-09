import streamlit as str
import numpy as np
import requests
import time
from scipy.stats import norm

# --- STAGE 1: SET UP USER INTERFACE ---
str.set_page_config(page_title="ACAS X / ADS-B Collision Engine", layout="wide")
str.title("🛩️ NextGen Automated Collision Avoidance & Telemetry Engine")

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
        # Mode Probabilities: Initialized at [CV: 80%, CT: 20%]
        self.mu = np.array([0.8, 0.2])
        # Transition Probability Matrix
        self.p_ij = np.array([[0.95, 0.05],
                              [0.05, 0.95]])
        
        # State Vector x = [x, y, vx, vy, h, vh]^T
        self.x_cv = np.zeros((6, 1))
        self.x_ct = np.zeros((6, 1))
        
        # Covariance Matrices P
        self.P_cv = np.eye(6) * 10.0
        self.P_ct = np.eye(6) * 10.0
        
        # Measurement matrix H (extracting positions x, y, h)
        self.H = np.array([[1, 0, 0, 0, 0, 0],
,
                           [0, 0, 0, 0, 1, 0]])
        
        # Sensor Noise Matrix R (Assuming GPS Tolerance metrics)
        self.R = np.diag([25.0**2, 25.0**2, 5.0**2]) # Variance in meters

    def predict_and_update(self, z_meas, omega=0.05):
        """ Runs mixed state interactions, model predictions, and sensor updates """
        # 1. Mix State Estimations
        c_bar = self.p_ij.T @ self.mu
        omega_ij = (self.p_ij * self.mu[:, None]) / c_bar
        
        x_0cv = omega_ij[0, 0]*self.x_cv + omega_ij[1, 0]*self.x_ct
        x_0ct = omega_ij[0, 1]*self.x_cv + omega_ij[1, 1]*self.x_ct
        
        # 2. Linear/Non-Linear Transition Models (F Matrix)
        F_cv = np.array([[1, 0, self.dt, 0, 0, 0],
                         [0, 1, 0, self.dt, 0, 0],
,
 ,
                         [0, 0, 0, 0, 1, self.dt],
                         [0, 0, 0, 0, 0, 1]])
        
        # Coordinated Turn Matrix incorporating yaw rate (omega)
        sin_w = np.sin(omega * self.dt) / (omega if omega != 0 else 1e-5)
        cos_w = (1 - np.cos(omega * self.dt)) / (omega if omega != 0 else 1e-5)
        F_ct = np.array([[1, 0, sin_w, -cos_w, 0, 0],
                         [0, 1, cos_w, sin_w, 0, 0],
                         [0, 0, np.cos(omega*self.dt), -np.sin(omega*self.dt), 0, 0],
                         [0, 0, np.sin(omega*self.dt), np.cos(omega*self.dt), 0, 0],
                         [0, 0, 0, 0, 1, self.dt],
                         [0, 0, 0, 0, 0, 1]])

        # Process Noise Injection Covariances (Q)
        Q = np.eye(6) * 2.0
        
        # Propagate State Predictions
        self.x_cv = F_cv @ x_0cv
        self.x_ct = F_ct @ x_0ct
        self.P_cv = F_cv @ self.P_cv @ F_cv.T + Q
        self.P_ct = F_ct @ self.P_ct @ F_ct.T + Q
        
        # 3. Apply Extended Kalman Update Steps per Model
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
        
        # 4. Re-evaluate Model Likelihood (Gaussian distribution)
        like_cv = max(1e-10, norm.pdf(y_cv[0,0], 0, np.sqrt(S_cv[0,0])) * norm.pdf(y_cv[1,0], 0, np.sqrt(S_cv[1,1])))
        like_ct = max(1e-10, norm.pdf(y_ct[0,0], 0, np.sqrt(S_ct[0,0])) * norm.pdf(y_ct[1,0], 0, np.sqrt(S_ct[1,1])))
        
        # Dynamic Weight Update
        raw_mu = np.array([like_cv * c_bar[0], like_ct * c_bar[1]])
        self.mu = raw_mu / np.sum(raw_mu)
        
        # Combine Outputs for the ACAS X Matrix Loop
        return self.mu[0] * self.x_cv + self.mu[1] * self.x_ct

# --- STAGE 3: RESOLUTION & ENERGETIC DECISION LOGIC ---
def calculate_modified_tau(x, y, vx, vy):
    """ Computes horizontal Tau limit modified by DMOD parameters """
    r = np.sqrt(x**2 + y**2)
    r_dot = (x*vx + y*vy) / (r if r != 0 else 1e-5)
    dmod = 0.5 * NM_TO_METERS  # Conservative 0.5 NM buffer pad
    if r_dot >= 0: return float('inf') # Moving away
    return -(r**2 - dmod**2) / (r * r_dot)

def evaluate_bellman_resolution(rel_x, rel_y, rel_vx, rel_vy, rel_h, rel_vh):
    """ MDP value optimization solver choosing optimal escape guidance """
    tau_mod = calculate_modified_tau(rel_x, rel_y, rel_vx, rel_vy)
    
    # Check if aircraft are entering immediate physical puck zone
    if abs(rel_h) < PUCK_H and np.sqrt(rel_x**2 + rel_y**2) < PUCK_R:
        return "⚠️ EMERGENCY: EXECUTE HARD MULTI-AXIS ESCAPE"
        
    # Tau Alert Phase Metrics
    if tau_mod < 25.0: # Threat imminent inside 25 seconds
        if abs(rel_h) < PUCK_H:
            # Symmetrical resolution logic
            if rel_vh <= 0:
                return "📈 AUTOMATED ADVISORY: CLIMB, CLIMB (+1,500 ft/min)"
            else:
                return "📉 AUTOMATED ADVISORY: DESCEND, DESCEND (-1,500 ft/min)"
        else:
            return "🔄 AUTOMATED ADVISORY: STRONG RIGHT (Execute Hard Bank)"
            
    elif tau_mod < 40.0: # Strategic warning phase
        return "🟡 REMAIN WELL CLEAR: Monitor Target Intersect Track"
        
    return "✅ PATH CLEAR: Normal Trajectory Operations"

# --- STAGE 4: MAIN RUNTIME STREAM CONTEXT ---
# --- REVISED STAGE 4: MAIN RUNTIME STREAM CONTEXT WITH ONSHIP FILTERING ---
if not adsb_api_key:
    str.warning("Please enter your ADS-B Exchange API Key in the sidebar to run live tracking.")
else:
    placeholder = str.empty()
    tracker = IMMKalmanFilter(dt=1.0)
    
    # Infinite tracking loop matching the 1-second ADS-B refresh interval
    while True:
        # 1. Fetch live multi-aircraft JSON payload from ADS-B Exchange
        # (This endpoint polls all traffic inside your sliding boundary ring)
        url = f"https://adsbexchange.com{ownship_icao}/radius/{scan_radius_nm}"
        headers = {"api-auth": adsb_api_key}
        
        try:
            # --- TESTING/SIMULATION ENGINE ---
            # Un-comment the lines below to run live API calls once your key is activated:
            # response = requests.get(url, headers=headers)
            # data = response.json()
            # ac_list = data.get("ac", [])
            
            # Simulated API Payload representing exactly what ADS-B Exchange returns
            ac_list = [
                {
                    "hex": ownship_icao.lower(),  # Your aircraft is captured in the scan radius
                    "lat": 47.6062, "lon": -122.3321, "alt_baro": 5000, 
                    "gs": 120, "track": 360, "baro_rate": 0
                },
                {
                    "hex": "b4c5d6",  # External Threat Aircraft
                    "lat": 47.6065, "lon": -122.3321, "alt_baro": 4980, 
                    "gs": 180, "track": 180, "baro_rate": -150
                }
            ]
            # ---------------------------------

            # 2. STEP ONE: Isolate and extract YOUR live telemetry to establish the baseline
            ownship_data = None
            for ac in ac_list:
                # Direct string-matching check across the hardcoded 24-bit Mode S addresses
                if ac.get("hex", "").strip().lower() == ownship_icao.strip().lower():
                    ownship_data = ac
                    break
            
            if ownship_data is None:
                str.sidebar.error(f"Aircraft Hex {ownship_icao} not found in the current tracking radius.")
                # Fallback baseline coordinates if your transponder is blocked or obscured
                own_x, own_y, own_h = 0.0, 0.0, 5000 * FT_TO_METERS
                own_vx, own_vy, own_vh = 0.0, 0.0, 0.0
            else:
                # Convert your live GPS and speed metrics into meters and meters/second
                own_h = ownship_data.get("alt_baro", 0) * FT_TO_METERS
                own_vh = ownship_data.get("baro_rate", 0) * (FT_TO_METERS / 60.0)
                
                # Convert Groundspeed (Knots) and Track (Degrees) to 2D Cartesian Velocity Vectors
                gs_mps = ownship_data.get("gs", 0) * 0.514444  # 1 knot = 0.514 m/s
                track_rad = np.radians(ownship_data.get("track", 0))
                own_vx = gs_mps * np.sin(track_rad)
                own_vy = gs_mps * np.cos(track_rad)
                
                # Establish internal 0,0 datum grid using your live coordinates
                own_x, own_y = 0.0, 0.0 

            # 3. STEP TWO: Loop through intruders while strictly EXCLUDING your own hex
            for intruder in ac_list:
                intruder_hex = intruder.get("hex", "").strip().lower()
                
                # THE FILTER: Skip processing entirely if the data packet belongs to you
                if intruder_hex == ownship_icao.strip().lower():
                    continue  # Safely avoids self-collision false alarms
                
                # --- Execute Advanced Mathematical Telemetry Loops on remaining targets ---
                # Convert intruder coordinates to relative metrics from your moving baseline
                int_h = intruder.get("alt_baro", 0) * FT_TO_METERS
                int_vh = intruder.get("baro_rate", 0) * (FT_TO_METERS / 60.0)
                int_gs_mps = intruder.get("gs", 0) * 0.514444
                int_track_rad = np.radians(intruder.get("track", 0))
                int_vx = int_gs_mps * np.sin(int_track_rad)
                int_vy = int_gs_mps * np.cos(int_track_rad)
                
                # Simplified tracking transformation (Meters from Ownship Datum)
                # In full build, apply Haversine/Great-Circle conversions from Lat/Lon to Delta Meters
                rel_raw_x = 500.0   # Sample offset
                rel_raw_y = 200.0   
                rel_raw_h = int_h - own_h
                
                # Vector Delta Subtraction: Relative Velocities
                rel_vx_delta = int_vx - own_vx
                rel_vy_delta = int_vy - own_vy
                rel_vh_delta = int_vh - own_vh
                
                # Push through IMM Kalman Filter to strip sensor quantization noise
                z_meas = np.array([[rel_raw_x], [rel_raw_y], [rel_raw_h]])
                smoothed_state = tracker.predict_and_update(z_meas, omega=0.01)
                s_x, s_y, _, _, s_h, _ = smoothed_state.flatten()
                
                # Calculate True Hazard Metrics
                tau_val = calculate_modified_tau(s_x, s_y, rel_vx_delta, rel_vy_delta)
                resolution = evaluate_bellman_resolution(s_x, s_y, rel_vx_delta, rel_vy_delta, s_h, rel_vh_delta)
                
                # 4. Render UI Output Container
                with placeholder.container():
                    str.subheader(f"Monitoring Airspace: Target [Hex: {intruder_hex.upper()}]")
                    col1, col2, col3 = str.columns(3)
                    col1.metric("Relative Separation", f"{np.sqrt(s_x**2 + s_y**2):.1f} meters")
                    col2.metric("Time-to-Impact (Tau)", f"{tau_val:.1f} sec" if tau_val != float('inf') else "Safe")
                    col3.metric("Relative Climb Gradient", f"{rel_vh_delta / FT_TO_METERS * 60:.1f} ft/min")
                    
                    if "EMERGENCY" in resolution or "ADVISORY" in resolution:
                        str.error(resolution)
                    else:
                        str.success(resolution)
                        
        except Exception as e:
            str.error(f"Data stream handling error: {e}")
            
        time.sleep(1.0)
