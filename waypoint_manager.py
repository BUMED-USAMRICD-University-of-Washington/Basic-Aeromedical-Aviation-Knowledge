import json
import os

class Waypoint:
    def __init__(self, name, lat, lon, alt, target_heading):
        self.name = name
        self.lat = lat
        self.lon = lon
        self.alt = alt
        self.target_heading = target_heading

    def to_dict(self):
        return self.__dict__

class WaypointManager:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.waypoints = []
        self.load_waypoints()

    def register_waypoint(self, name, lat, lon, alt, heading):
        new_wp = Waypoint(name, lat, lon, alt, heading)
        self.waypoints.append(new_wp)
        self.save_waypoints()
        print(f"✅ Registered Waypoint: {name}")

    def save_waypoints(self):
        """Persists waypoints to config.json"""
        data = {"waypoints": [wp.to_dict() for wp in self.waypoints]}
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=4)

    def load_waypoints(self):
        """Loads waypoints from config.json"""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                data = json.load(f)
                self.waypoints = [Waypoint(**wp) for wp in data.get("waypoints", [])]

    def get_active_waypoint(self, index=0):
        if index < len(self.waypoints):
            return self.waypoints[index]
        return None
