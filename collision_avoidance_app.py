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
if not adsb_api_key:
    str.warning("Please enter your ADS-B Exchange API Key in the sidebar to run live tracking.")
else:
    # Simulated Live Telemetry Container
    placeholder = str.empty()
    tracker = IMMKalmanFilter(dt=1.0)
    
    # Synthetic / Placeholder tracking coordinates simulating an un-throttled feed
    sim_t = 0
    while True:
        sim_t += 1
        
        # Real Architecture Hook: 
        # url = f"https://adsbexchange.com{ownship_icao}/radius/{scan_radius_nm}"
        # headers = {"api-auth": adsb_api_key}
        # data = requests.get(url, headers=headers).json()
        
        # Simulating a high-speed parallel runway blunder scenario
        intruder_raw_x = 1200 - (sim_t * 55)   # Slicing inward horizontally
        intruder_raw_y = 400 - (sim_t * 5)
        intruder_raw_h = 3000 * FT_TO_METERS - (sim_t * 2.1 * FT_TO_METERS) # Descending jump
        
        # Injecting random quantization and sensor noise
        z_meas = np.array([[intruder_raw_x + np.random.normal(0, 15)],
                           [intruder_raw_y + np.random.normal(0, 15)],
                           [intruder_raw_h + np.random.normal(0, 4)]])
        
        # Push through sensor noise filters
        smoothed_state = tracker.predict_and_update(z_meas, omega=0.03)
        
        # Extract relative state geometries (Assuming ownship holds stationary baseline)
        s_x, s_y, s_vx, s_vy, s_h, s_vh = smoothed_state.flatten()
        
        tau_val = calculate_modified_tau(s_x, s_y, s_vx, s_vy)
        resolution = evaluate_bellman_resolution(s_x, s_y, s_vx, s_vy, s_h, s_vh)
        
        # Render Flight Deck Matrix Displays
        with placeholder.container():
            col1, col2, col3 = str.columns(3)
            col1.metric("Smoothed Slant Range", f"{np.sqrt(s_x**2 + s_y**2):.1f} meters")
            col2.metric("Modified Tau Domain", f"{tau_val:.1f} seconds" if tau_val != float('inf') else "Safe")
            col3.metric("Filtered Vert Rate (h_dot)", f"{s_vh / FT_TO_METERS * 60:.1f} ft/min")
            
            # Print Alert Outputs and Model Confidence Indexes
            if "EMERGENCY" in resolution or "ADVISORY" in resolution:
                str.error(resolution)
            else:
                str.success(resolution)
                
            str.text(f"IMM Confidence Metrics -> Straight Flight Model (CV): {tracker.mu[0]*100:.1f}% | Bank Turning Model (CT): {tracker.mu[1]*100:.1f}%")
            
        time.sleep(1.0)
