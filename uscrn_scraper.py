# uscrn_scraper.py
# Ingests live, pristine rural baseline temperatures from NOAA USCRN networks

import pandas as pd
import requests
from io import StringIO
from datetime import datetime

# 1. Map target NWS City stations to their nearest pristine rural USCRN station
# USCRN stations are identified by their WBAN number or site name.
USCRN_STATION_MAP = {
    "KNYC": {"uscrn_id": "14735", "name": "NY Millbrook 3 W"},     # Rural baseline for NYC
    "KORD": {"uscrn_id": "04808", "name": "IL Shabbona 5 NNE"},    # Rural baseline for Chicago
    "KPHX": {"uscrn_id": "23199", "name": "AZ Tucson 11 W"},       # Rural desert baseline for Phoenix
    "KSEA": {"uscrn_id": "94299", "name": "WA Quinault 4 NE"},     # Pristine baseline for Seattle
    "KFFC": {"uscrn_id": "53838", "name": "GA Watkinsville 5 S"}   # Rural baseline for Atlanta
}

def fetch_rural_baseline(target_icao):
    """
    Fetches the most recent hourly temperature from the nearest pristine USCRN station.
    """
    if target_icao not in USCRN_STATION_MAP:
        raise ValueError("Target ICAO not mapped to a USCRN baseline station.")
    
    uscrn_station = USCRN_STATION_MAP[target_icao]
    station_wban = uscrn_station["uscrn_id"]
    current_year = datetime.utcnow().year
    
    # NOAA's public USCRN hourly data directory (Plain text fixed-width format)
    # Formatted to access the current year's text file for the specific station
    data_url = f"https://www.ncei.noaa.gov/pub/data/uscrn/products/hourly02/{current_year}/CRNH0203-{current_year}-{station_wban}.txt"
    
    try:
        response = requests.get(data_url)
        response.raise_for_status()
        
        # USCRN files are fixed-width text. We extract the relevant columns: 
        # Date, Time, and T_CALC (Calculated Air Temperature in Celsius)
        columns = ["WBANNO", "UTC_DATE", "UTC_TIME", "LST_DATE", "LST_TIME", "CRX_VN", 
                   "LONGITUDE", "LATITUDE", "T_CALC", "T_HR_AVG", "T_MAX", "T_MIN", "P_CALC"]
        
        # Read the raw text into a pandas DataFrame
        df = pd.read_csv(StringIO(response.text), sep="\s+", names=columns, usecols=["LST_DATE", "LST_TIME", "T_CALC"], na_values="-9999.0")
        
        # Drop any rows where temperature data is missing or offline
        df = df.dropna(subset=["T_CALC"])
        
        # Extract the absolute most recent temperature reading (last row)
        latest_reading = df.iloc[-1]
        t_rural_celsius = float(latest_reading["T_CALC"])
        
        # Convert Celsius to Fahrenheit for US Aviation standards
        t_rural_fahrenheit = (t_rural_celsius * 9/5) + 32
        
        return {
            "status": "SUCCESS",
            "target_city_icao": target_icao,
            "uscrn_baseline_name": uscrn_station["name"],
            "timestamp_local": f"{latest_reading['LST_DATE']} {latest_reading['LST_TIME']}",
            "t_rural_f": round(t_rural_fahrenheit, 2)
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status": "ERROR",
            "message": f"Failed to retrieve USCRN data: {e}"
        }

# ==========================================
# Example Execution
# ==========================================
# if __name__ == "__main__":
#     # Fetching the pristine rural baseline for New York City
#     baseline_data = fetch_rural_baseline("KNYC")
#     print(baseline_data)
