import csv
from datetime import datetime, timedelta
import astropy.coordinates as coord
import astropy.units as u
from astropy.time import Time
import numpy as np


def get_user_inputs(telemetry_override=None):
    print("--- GPS Station Lunar Log Configurator ---")
    lat = float(input("Enter Latitude in decimal degrees (e.g., 47.6062): "))
    lon = float(input("Enter Longitude in decimal degrees (e.g., -122.3321): "))
    elevation = float(input("Enter station elevation in meters (e.g., 45.0): "))
    year = int(input("Enter the target year (e.g., 2026): "))
    return year, lat, lon, elevation


def calculate_and_export_lunar_log():
    year, lat, lon, elevation_m = get_user_inputs()
    print(f"\n[Processing] Modeling 1-year window path coordinates...")

    observer_loc = coord.EarthLocation(
        lat=lat * u.deg, lon=lon * u.deg, height=elevation_m * u.m
    )

    start_time = datetime(year, 1, 1, 0, 0, 0)
    end_time = datetime(year, 12, 31, 23, 0, 0)
    time_steps = []

    current = start_time
    while current <= end_time:
        time_steps.append(current)
        current += timedelta(hours=1)

    astropy_times = Time(time_steps)
    alt_az_frame = coord.AltAz(obstime=astropy_times, location=observer_loc)
    moon_coords = coord.get_moon(astropy_times).transform_to(alt_az_frame)

    alts = moon_coords.alt.deg
    azs = moon_coords.az.deg

    filename = f"lunar_trajectory_log_{year}_{lat:.2f}_{lon:.2f}.csv"

    # Export massive 8,760 hourly row dataset to file system
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "Timestamp_UTC",
                "Moon_Altitude_Degrees",
                "Moon_Azimuth_Degrees",
                "Status_Horizon",
            ]
        )

        for i in range(len(time_steps)):
            horizon_status = "Visible" if alts[i] >= 0 else "Obscured_By_Earth"
            writer.writerow(
                [
                    time_steps[i].strftime("%Y-%m-%d %H:%M:%S"),
                    round(alts[i], 3),
                    round(azs[i], 3),
                    horizon_status,
                ]
            )

    print(f"=============================================")
    print(f"[Success] Core data matrix completely mapped.")
    print(f"Output saved to local path: '{filename}'")
    print(f"Total entries processed:    {len(time_steps)} hours")
    print(f"=============================================")


if __name__ == "__main__":
    calculate_and_export_lunar_log()
