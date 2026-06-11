""" aviation_icing.py """
""" Structural Degradation & Thermodynamic Ice Accretion Engine """
""" Optimized: Else-Less Guard Clauses | 15-Decimal Precision | Numba Kernels """
import multiprocessing as mp
import math
import telemetry_link

""" --- HARDWARE ABSTRACTION LAYER (HAL) --- """
try:
    import cupy as xp
    from numba import dummy_njit as njit
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Matrix Allocation Active (Icing Engine)")
except ImportError:
    import numpy as xp
    from numba import njit
    HAS_GPU = False
    print("CPU Fallback: Numba Vectorization Active (Icing Engine)")


""" ===================================================================== """
""" --- PURE MATH KERNELS (THE BASEMENT MATHEMATICIANS) --- """
""" ===================================================================== """

@njit(fastmath=True)
def compute_liquid_water_content(temp_c, relative_humidity_pct):
    """ Calculates the density of supercooled water droplets in the air mass. """
    
    """ GUARD 1: Temperature is too warm for ice formation """
    if temp_c > 2.0:
        return 0.0

    """ GUARD 2: Temperature is too cold (Moisture already frozen into dry crystals) """
    if temp_c < -40.0:
        return 0.0

    """ GUARD 3: Air is too dry to support droplet suspension """
    if relative_humidity_pct < 70.0:
        return 0.0

    """ HAPPY PATH: Calculate LWC (g/m^3) using approximation model """
    """ Peak LWC typically occurs around -10C to -15C """
    temp_factor = 1.0 - abs(temp_c + 12.0) / 28.0
    
    """ Precision clamp to prevent negative moisture """
    if temp_factor < 0.0:
        temp_factor = 0.0
        
    lwc_g_m3 = (relative_humidity_pct / 100.0) * temp_factor * 2.5
    return lwc_g_m3

@njit(fastmath=True)
def calculate_ice_accumulation_rate(lwc_g_m3, velocity_mps, collection_efficiency, dt):
    """ Calculates the raw mass of ice impacting the leading edges per second. """
    
    """ GUARD 1: No moisture or no forward velocity """
    if lwc_g_m3 <= 0.0 or velocity_mps <= 0.0:
        return 0.0

    """ HAPPY PATH: M_ice = LWC * V * E * dt """
    """ Convert g/m^3 to kg/m^3 for standard aerospace units """
    lwc_kg_m3 = lwc_g_m3 / 1000.0
    
    mass_rate_kg_s = lwc_kg_m3 * velocity_mps * collection_efficiency
    accumulated_kg = mass_rate_kg_s * dt
    
    return accumulated_kg

@njit(fastmath=True)
def compute_aerodynamic_penalties(current_ice_mass_kg, base_cd0, base_stall_kts):
    """ Translates physical ice mass into aerodynamic degradation for the FSM. """
    
    """ GUARD 1: Clean airframe """
    if current_ice_mass_kg <= 0.0:
        return base_cd0, base_stall_kts

    """ HAPPY PATH: Calculate scaling penalties """
    """ Ice severely disrupts laminar flow, exponentially increasing parasite drag """
    drag_multiplier = 1.0 + (current_ice_mass_kg * 0.005)
    new_cd0 = base_cd0 * drag_multiplier
    
    """ Stall speed increases due to loss of lift coefficient and added weight """
    stall_multiplier = math.sqrt(1.0 + (current_ice_mass_kg * 0.002))
    new_stall_kts = base_stall_kts * stall_multiplier
    
    return new_cd0, new_stall_kts


""" ===================================================================== """
""" --- THE ORCHESTRATOR (THE THERMODYNAMIC MANAGER) --- """
""" ===================================================================== """

class AviationIcingEngine:
    """ Manages structural health monitoring and feeds degradation data to the PID loop. """
    
    @njit(fastmath=True)
    def __init__(self):
        """ 15-Decimal Default Baselines """
        self.total_ice_mass_kg = 0.000000000000000
        self.COLLECTION_EFFICIENCY = 0.450000000000000
        self.BASE_CD0 = 0.020000000000000
        self.BASE_STALL_KTS = 110.000000000000000

    @njit(fastmath=True)
    def trigger_deicing_boots(self):
        """ Simulates pneumatic boot actuation to shed accumulated mass. """
        
        """ GUARD 1: No ice to shed """
        if self.total_ice_mass_kg <= 0.0:
            return {"status": "CLEAN_AIRFRAME"}

        """ HAPPY PATH: Shed 85 percent of accumulated mass """
        shed_mass = self.total_ice_mass_kg * 0.850000000000000
        self.total_ice_mass_kg -= shed_mass
        
        return {"status": "DEICING_ACTUATED", "mass_shed_kg": round(float(shed_mass), 15)}
    
    @njit(fastmath=True)
    def update_structural_degradation(self, env_payload, ship_velocity_mps, dt=0.1):
        """ Master cycle for thermodynamic tracking. Gathers NOAA data and applies physics. """
        
        temp_c = float(env_payload.get('temp_c', 15.0))
        rh_pct = float(env_payload.get('relative_humidity', 50.0))
        
        """ 1. Calculate environmental water density """
        lwc = compute_liquid_water_content(temp_c, rh_pct)
        
        """ GUARD 1: Dry or warm air (Passive sublimation/melting) """
        if lwc <= 0.0:
            if temp_c > 2.0 and self.total_ice_mass_kg > 0.0:
                self.total_ice_mass_kg -= (0.5 * dt)
                if self.total_ice_mass_kg < 0.0:
                    self.total_ice_mass_kg = 0.0
            return self._export_payload()

        """ 2. Calculate impact accretion """
        added_mass = calculate_ice_accumulation_rate(
            float(lwc), float(ship_velocity_mps), self.COLLECTION_EFFICIENCY, float(dt)
        )
        self.total_ice_mass_kg += added_mass
        
        """ 3. Export global telemetry for the PID controllers """
        return self._export_payload()
    
    @njit(fastmath=True)
    def _export_payload(self):
        """ Packages the 15-decimal float data for the telemetry bus. """
        
        new_cd0, new_stall = compute_aerodynamic_penalties(
            float(self.total_ice_mass_kg), self.BASE_CD0, self.BASE_STALL_KTS
        )
        
        payload = {
            "ice_mass_kg": round(float(self.total_ice_mass_kg), 15),
            "dynamic_cd0": round(float(new_cd0), 15),
            "dynamic_stall_kts": round(float(new_stall), 15)
        }
        
        telemetry_link.update_global_state("thermodynamics", "icing_status", payload)
        return payload
