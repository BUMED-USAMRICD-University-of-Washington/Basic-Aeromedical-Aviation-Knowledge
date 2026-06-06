from datetime import datetime, timedelta
import astropy.coordinates as coord
import astropy.units as u
from astropy.time import Time
import matplotlib.pyplot as plt
import numpy as np


def get_user_inputs():
    """Prompts the user for decimal GPS values and year via terminal input."""
    print("--- Local Lunar Path Calculator Configuration ---")
    try:
        # Prompt for Latitude
        lat = float(input("Enter Latitude in decimal degrees (e.g., 47.6062): "))
        if not -90 <= lat <= 90:
            raise ValueError("Latitude must be between -90 and 90.")

        # Prompt for Longitude
        lon = float(
            input("Enter Longitude in decimal degrees (e.g., -122.3321): ")
        )
        if not -180 <= lon <= 180:
            raise ValueError("Longitude must be between -180 and 180.")

        # Prompt for Elevation
        elevation = float(
            input("Enter station elevation in meters (e.g., 45.0): ")
        )

        # Prompt for Target Year
        year = int(input("Enter the target year (e.g., 2026): "))

        return year, lat, lon, elevation

    except ValueError as e:
        print(f"\n[Input Error]: {e}. Please enter valid numbers.")
        exit(1)


def calculate_lunar_path(year, lat, lon, elevation_m):
    """Calculates the Moon's local horizon coordinates using Astropy

    based on the user's custom decimal GPS input.
    """
    print(f"\n[Processing] Computing 8,760 hourly data points for {year}...")

    # Define location using inputs
    observer_loc = coord.EarthLocation(
        lat=lat * u.deg, lon=lon * u.deg, height=elevation_m * u.m
    )

    # Generate hourly steps for the selected year
    start_time = datetime(year, 1, 1, 0, 0, 0)
    end_time = datetime(year, 12, 31, 23, 0, 0)
    time_steps = []

    current = start_time
    while current <= end_time:
        time_steps.append(current)
        current += timedelta(hours=1)

    # Convert to Astropy tracking frames
    astropy_times = Time(time_steps)
    alt_az_frame = coord.AltAz(obstime=astropy_times, location=observer_loc)

    # Run orbital math calculations
    moon_coords = coord.get_moon(astropy_times).transform_to(alt_az_frame)

    return time_steps, moon_coords.alt.deg, moon_coords.az.deg


if __name__ == "__main__":
    # 1. Capture dynamic user coordinates
    target_year, user_lat, user_lon, user_elev = get_user_inputs()

    # 2. Run Orbit Engine
    times, alts, azs = calculate_lunar_path(
        target_year, user_lat, user_lon, user_elev
    )

    # 3. Extract key metrics (Highest altitude pass of the year)
    max_idx = np.argmax(alts)

    print("\n=============================================")
    print("          ANNUAL LUNAR ANALYSIS             ")
    print("=============================================")
    print(f"Target Location:  {user_lat:.4f}°, {user_lon:.4f}°")
    print(f"Peak Altitude:    {alts[max_idx]:.2f}° above horizon")
    print(f"Peak Azimuth:     {azs[max_idx]:.2f}° heading")
    print(f"Peak Time (UTC):  {times[max_idx]}")
    print("=============================================")

    # 4. Generate Visualization
    plt.figure(figsize=(12, 6))
    plt.plot(
        times[:48],
        alts[:48],
        label="Calculated Moon Path",
        color="crimson",
        linewidth=2,
    )
    plt.axhline(0, color="black", linestyle="--", alpha=0.5, label="Horizon")
    plt.title(
        f"First 48-Hour Lunar Arc at Custom GPS ({user_lat:.4f}, {user_lon:.4f}) for {target_year}"
    )
    plt.xlabel("Timeline")
    plt.ylabel("Elevation Vector (Degrees)")
    plt.grid(True, alpha=0.2)
    plt.legend()

    print("\n[Success] Interactive map data built. Use plt.show() to view graph.")
