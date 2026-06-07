## Dedication & Professional Resources

This project is dedicated to the instructors at Green River College, whose guidance provided the foundational framework for this aviation modeling architecture.

* **Academic Partner:** [Green River College Aviation Technology](https://www.greenriver.edu/students/academics/areas-of-interest/program-maps/trades-industrial-tech-aviation-natural-resources/aviation-technology/index.html)
* **Legal & Professional Reference:** [Fox Rothschild Aviation Practice](https://www.foxrothschild.com/aviation)

✈️ Basic Aviation Knowledge - Airport Reporting Models
======================================================

This repository houses a suite of proprietary, physics-driven predictive models and a live Streamlit dashboard. It is designed to simulate exact Official Climatological Record temperatures (T_station), localized microclimate offsets, and high-precision Density Altitude thresholds for aviation performance.

By coupling macro-atmospheric fluid dynamics with the specific heat capacity of physical ground-station enclosures, this architecture calculates highly precise environmental baselines that strip away structural and hardware-induced temperature errors.

🌟 Core Features
----------------

-   Official Climatological Record Prediction: Mathematically predicts physical thermodynamics, including evaporative cooling penalties, thermal mass lag, and solar albedo variants.

-   Live Flight Telemetry Mode: Seamlessly transitions from a static pre-flight planning calculator to an active in-flight navigational tool. Interfaces directly with USB DGPS/RTK and barometric elevation dongles via NMEA serial data to stream real-time coordinates and altitudes directly into the performance matrices.

-   Complex Microclimate Geography Modules:

    -   SEA (Seattle): Puget Sound Convergence Zone cooling and Olympic Mountain downsloping.

    -   ORD (Chicago): Lake Michigan breeze frontal boundary penetration drops.

    -   PHX (Phoenix): Urban Heat Island (UHI) asphalt thermal mass retention and decay.

    -   SFO (San Francisco): Harmonic superposition for the marine inversion layer.

-   Volumetric Radar Verification: Utilizes 2D spatial polygons and 3D altitude trackpoints to mathematically verify if a target coordinate sits within a radar blind spot, preventing the model from relying on radar data that overshoots ground-level surface conditions.

-   Pristine Baseline Routing: Automatically ingests live, pristine rural baseline temperatures via fixed-width text feeds to calculate accurate Urban Heat Island gradients and isolate structural heat multipliers.

🛠️ Installation & Setup
------------------------

1.  Clone the Repository:

    git clone [https://github.com/FADM-DCMN-CORY-A-HOFSTAD-USN/Basic-Aviation-Knowledge.git](https://www.google.com/search?q=https://github.com/FADM-DCMN-CORY-A-HOFSTAD-USN/Basic-Aviation-Knowledge.git&authuser=1)

    cd Basic-Aviation-Knowledge

2.  Install Dependencies:

    Ensure you have Python 3.9+ installed, then run:

    pip install -r requirements.txt

3.  Launch the Dashboard:

    Start the local Streamlit server to open the interface in your browser:

    streamlit run app.py

4.  Live Telemetry (In-Flight Operations):

    To utilize live tracking, plug your compatible USB DGPS dongle into your device, launch the app, and switch the sidebar toggle to "Live Flight Mode." (Note: Verify and update the target COM/tty port in live_telemetry.py based on your operating system).

📚 Core Dependencies & Architecture
-----------------------------------

This repository relies on a highly specific stack of mathematical, spatial, and hardware-interfacing Python libraries to process live thermodynamic variables and DGPS telemetry.

-   streamlit: Drives the interactive web dashboard (app.py), allowing real-time switching between static planning models and live in-flight telemetry modes.

-   pandas: Parses complex, fixed-width text data from the automated USCRN API and processes tabular coordinate exports from GIS systems.

-   numpy: Powers the heavy mathematical arrays required for the thermodynamic equations, including urban thermal decay constants and lake breeze frontal boundary limits.

-   matplotlib: Generates the 2D spatial cross-sections and temperature timeline visualizations rendered directly on the Streamlit dashboard.

-   requests: Handles the automated HTTP requests to fetch pristine rural baseline temperatures (T_rural) for Urban Heat Island calculations.

-   shapely: Constructs the mathematical 2D bounding boxes to verify if a specific coordinate sits inside an active radar footprint.

-   pyserial: Opens the hardware serial ports (COM/tty) to physically interface with USB DGPS and barometric elevation dongles.

-   pynmea2: Decodes the raw $GPGGA and $GNGGA satellite text strings streaming from the dongle into clean, usable latitude, longitude, and elevation variables.

📂 Key Module Directory
-----------------------

-   app.py: The main Streamlit execution application and UI router.

-   live_telemetry.py: Hardware interfacing script for USB DGPS/RTK streams.

-   sensor_thermodynamics.py: Calculates evaporative cooling penalties and thermal mass lag for various physical enclosure types.

-   spatial_polygon_builder.py & radar_geometry_parser.py: The 2D/3D spatial verification engines for radar beam coverage.

-   uscrn_scraper.py: Automated fetching of live rural background temperatures.

-   config.json: The central registry for Urban Heat Island modifiers and specific reporting target coordinates.

*Derived from metrics aligned with standard Aviation Weather operational requirements.*
