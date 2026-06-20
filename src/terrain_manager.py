import math
import rasterio
from pathlib import Path

class AviationTerrainEngine:
    def __init__(self, data_directory_path: str):
        self.base_dir = Path(data_directory_path)
        
        # Memory Caching: Cache the currently active tile mesh data
        self.active_tile_id = None
        self.active_dataset = None
        self.active_matrix = None

    def update_aircraft_position(self, current_lat: float, current_lon: float):
        """
        Call this function inside your flight loop. 
        It checks if the aircraft crossed a 1-degree threshold and automatically swaps files.
        """
        # Calculate exactly which file matches the current coordinates
        lat_floor = math.floor(current_lat)
        lon_floor = math.floor(current_lon)
        
        # Trace regional parent folders
        region_lat = (lat_floor // 10) * 10
        region_lon = (lon_floor // 10) * 10
        
        region_name = f"{region_lat:+03d}{region_lon:+04d}"
        tile_name = f"{lat_floor:+03d}{lon_floor:+04d}.tif"
        
        target_tile_id = f"{region_name}/{tile_name}"
        
        # If the plane is still in the same grid square, bypass loading routines to save CPU cycles
        if self.active_tile_id == target_tile_id:
            return

        # Swap the active tile dataset in memory
        self.unload_active_tile()
        
        target_file_path = self.base_dir / region_name / tile_name
        
        if target_file_path.exists():
            try:
                # Open the new file layer and cache it
                self.active_dataset = rasterio.open(target_file_path)
                self.active_matrix = self.active_dataset.read(1)
                self.active_tile_id = target_tile_id
                print(f"[ENGINE INFO] Seamless transition to new terrain tile: {target_tile_id}")
            except Exception as e:
                print(f"[ENGINE ERROR] Failed loading terrain grid matrix: {e}")
                self.reset_to_sea_level()
        else:
            # Handle open water / unmapped flight areas safely without crashing the client app
            self.reset_to_sea_level()

    def get_ground_elevation(self, latitude: float, longitude: float) -> float:
        """Instantly extracts the terrain height beneath the plane in milliseconds"""
        if self.active_dataset is None or self.active_matrix is None:
            return 0.0 # Default to Sea Level
            
        try:
            # Map global GPS coordinates directly to image row/column array indices
            row, col = self.active_dataset.index(longitude, latitude)
            
            # Constrain parameters to image limits
            row = max(0, min(row, self.active_matrix.shape[0] - 1))
            col = max(0, min(col, self.active_matrix.shape[1] - 1))
            
            return float(self.active_matrix[row, col])
        except Exception:
            return 0.0

    def unload_active_tile(self):
        """Unloads data components safely to prevent background memory leaks"""
        if self.active_dataset:
            self.active_dataset.close()
        self.active_dataset = None
        self.active_matrix = None
        self.active_tile_id = None

    def reset_to_sea_level(self):
        self.unload_active_tile()
        self.active_tile_id = "SEA_LEVEL_WATER"


# ==========================================
# SIMULATED APPLICATION EXECUTION RUNTIME
# ==========================================
if __name__ == "__main__":
    # Point the module to your repository folder path
    engine = AviationTerrainEngine(r"E:\GitHub\Basic-Aviation-Knowledge\src\earth")
    
    # Flight Simulation Telemetry Data Stream (e.g. cruising toward a mountain range)
    simulated_flight_path = [
        {"lat": 47.125, "lon": -122.842, "alt_msl": 1500},
        {"lat": 47.581, "lon": -122.311, "alt_msl": 1500},
        {"lat": 48.021, "lon": -121.905, "alt_msl": 1500} # Crosses grid margin boundary line
    ]
    
    for telemetry in simulated_flight_path:
        # 1. Update positioning coordinates
        engine.update_aircraft_position(telemetry["lat"], telemetry["lon"])
        
        # 2. Perform ground impact assessment
        ground_height = engine.get_ground_elevation(telemetry["lat"], telemetry["lon"])
        height_agl = telemetry["alt_msl"] - ground_height
        
        print(f" Aircraft GPS Point: ({telemetry['lat']}, {telemetry['lon']}) | Ground: {ground_height:.1f}m | Clearance: {height_agl:.1f}m")
