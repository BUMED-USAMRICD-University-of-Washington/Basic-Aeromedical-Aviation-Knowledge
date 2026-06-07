# waypoint_manager.py
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
