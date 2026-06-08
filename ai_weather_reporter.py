from airport_data_manager import manager
import wind_dynamics
import fog_thermodynamics

def generate_ai_metar(ident):
    # 1. Fetch Context (Infrastructure Layer)
    airport = manager.get_airport(ident)
    if not airport: return "INVALID STATION"
    
    # 2. Fetch Observations (Meteorological Layer)
    wind_data = wind_dynamics.run_wind_layer()
    fog_data = fog_thermodynamics.run_fog_layer()
    
    # 3. Assemble the string
    metar = f"{ident} 072100Z {wind_data['wind_speed_mph']}KT ..." 
    return metar
