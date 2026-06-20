import math
import h5py
from pathlib import Path

# Configured target grid density matching our dual-exporter script
GRID_RESOLUTION = 1200

class AviationTerrainEngine:
    """
    High-performance spatial grid manager. Automatically streams and caches
    binary 1°x1° .h5 terrain matrix grids based on target GPS coordinates.
    """
    def __init__(self, data_directory_path: str):
        self.base_dir = Path(data_directory_path)
        
        # Memory Caching layer: Ensures minimal disk read bottlenecks during flight
        self.active_tile_id = None
        self.active_matrix = None

    def update_aircraft_position(self, current_lat: float, current_lon: float):
        """
        Monitors spatial boundary thresholds. If the aircraft steps outside
        the active 1-degree matrix layer, the old tile unloads and the new one swaps in.
        """
        lat_floor = math.floor(current_lat)
        lon_floor = math.floor(current_lon)
        
        # Compute 10°x10° parental directory indexing framework
        region_lat = (lat_floor // 10) * 10
        region_lon = (lon_floor // 10) * 10
        
        region_name = f"{region_lat:+03d}{region_lon:+04d}"
        tile_name = f"{lat_floor:+03d}{lon_floor:+04d}.h5"
        
        target_tile_id = f"{region_name}/{tile_name}"
        
        # Bypass heavy IO system operations if the aircraft is tracking within the same sector
        if self.active_tile_id == target_tile_id:
            return

        self.unload_active_tile()
        target_file_path = self.base_dir / region_name / tile_name
        
        if target_file_path.exists():
            try:
                # Direct binary matrix block transfer straight into RAM
                with h5py.File(target_file_path, 'r') as h5_file:
                    self.active_matrix = h5_file["elevation"][:]
                    self.active_tile_id = target_tile_id
            except Exception as e:
                print(f"[TERRAIN ENGINE ERROR] Fault reading matrix array: {e}")
                self.reset_to_sea_level()
        else:
            # Fallback configuration handling ocean segments / unmapped territories safely
            self.reset_to_sea_level()

    def get_ground_elevation(self, latitude: float, longitude: float) -> float:
        """
        Sub-millisecond array cell index transformation logic.
        Extracts elevation in meters exactly underneath the target vector.
        """
        if self.active_matrix is None:
            return 0.0 # Standard Sea Level Default
            
        try:
            lat_floor = math.floor(latitude)
            lon_floor = math.floor(longitude)
            
            # Map global GPS decimal remainders to array coordinates (0.0 to 1.0 scaling)
            lat_fraction = latitude - lat_floor
            lon_fraction = longitude - lon_floor
            
            # Invert latitude index tracking because image matrices layout grids from Top to Bottom
            row_idx = int((1.0 - lat_fraction) * (GRID_RESOLUTION - 1))
            col_idx = int(lon_fraction * (GRID_RESOLUTION - 1))
            
            # Bound memory lookups tightly to avoid buffer boundary errors
            row_idx = max(0, min(row_idx, GRID_RESOLUTION - 1))
            col_idx = max(0, min(col_idx, GRID_RESOLUTION - 1))
            
            return float(self.active_matrix[row_idx, col_idx])
        except Exception:
            return 0.0

    def unload_active_tile(self):
        """Purges active matrix blocks out of tracking lines to keep heap footprint low"""
        self.active_matrix = None
        self.active_tile_id = None

    def reset_to_sea_level(self):
        self.unload_active_tile()
        self.active_tile_id = "OPEN_WATER_BASE"
