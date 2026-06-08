
## Dedication & Professional Resources

This project is dedicated to the instructors at Green River College, whose guidance provided the foundational framework for this aviation modeling architecture.

* **Academic Partner:** [Green River College Aviation Technology](https://www.greenriver.edu/students/academics/areas-of-interest/program-maps/trades-industrial-tech-aviation-natural-resources/aviation-technology/index.html)
* **Legal & Professional Reference:** [Fox Rothschild Aviation Practice](https://www.foxrothschild.com/aviation)

Basic Aviation Knowledge - Airport Reporting Models
======================================================

This repository houses a suite of proprietary, physics-driven predictive models and a live Streamlit dashboard. It is designed to simulate exact Official Climatological Record temperatures (T_station), localized microclimate offsets, and high-precision Density Altitude thresholds for aviation performance.

By coupling macro-atmospheric fluid dynamics with the specific heat capacity of physical ground-station enclosures, this architecture calculates highly precise environmental baselines that strip away structural and hardware-induced temperature errors.

Core Features
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

-   Advanced Entry Engine: Atmospheric entry management utilizing Sutton-Graves stagnation heat flux models and PID-controlled bank-angle correction for storm drift.

-   Energy Management: Automated S-Turn maneuver injection to dissipate kinetic energy during high-angle or "too hot" arrivals.

-   Performance Kernels: Hot-path physics calculations (Rossby dynamics, icing models, thermodynamics) are accelerated via **Numba (`njit`)** and integrated multicore processing for near-real-time throughput.

-   Config Validation: Enforces strict Pydantic schema validation for all inputs (mass, area, G-loads). Rejects malformed configuration files before simulation start.

-   Atomic Telemetry: Utilizes file-locking (`fcntl`) for all binary telemetry exports (Lockheed 1553B, NASA HDF5), ensuring data integrity during high-throughput flight loops.

-   Protocol Integrity: Automated pre-flight checklists via `cli_main.py` verify that all six aerospace export protocols (Boeing, NASA, Lockheed, Axiom, Northrop, OAAM) are live and writing valid data.

Installation & Setup
------------------------

1.  Clone the Repository:

    git clone [https://github.com/FADM-DCMN-CORY-A-HOFSTAD-USN/Basic-Aviation-Knowledge.git](https://www.google.com/search?q=https://github.com/FADM-DCMN-CORY-A-HOFSTAD-USN/Basic-Aviation-Knowledge.git&authuser=1)

    cd Basic-Aviation-Knowledge

2.  Install Dependencies:

    Ensure you have Python 3.9+ installed, then run:

    pip install -r requirements.txt

### Validation & Readiness

Verify all protocol channels and configurations:

Bash

```
python cli_main.py validate

```

### Launch Mission Control

Start the cockpit TUI with tactical profile:

Bash

```
python app.py --mode TACTICAL --target Earth

```

### Performance Reporting

Export high-fidelity trajectory data for FAA/Mission Review:

Bash

```
python aviation_matrix_export.py

```

### Auto-Documentation

Generate/Refresh documentation from current code docstrings:

Bash

```
python cli_main.py regen-docs

```

Live Telemetry (In-Flight Operations):

    To utilize live tracking, plug your compatible USB DGPS dongle into your device, launch the app, and switch the sidebar toggle to "Live Flight Mode." (Note: Verify and update the target COM/tty port in live_telemetry.py based on your operating system).

Core Dependencies & Architecture
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

-   textual

-   "typer[all]"

-   pydantic

-   pyserial

-   pyttsx3

-   cupy-cuda12x

-   matplotlib

-   astropy

-   requests

-   psutil

-   h5py          # For multi-dimensional HDF5 scientific data

-   struct        # For binary CCSDS-style packet packing (built-in)

Key Module Directory
-----------------------

-   app.py: The main Streamlit execution application and UI router.

-   live_telemetry.py: Hardware interfacing script for USB DGPS/RTK streams.

-   sensor_thermodynamics.py: Calculates evaporative cooling penalties and thermal mass lag for various physical enclosure types.

-   spatial_polygon_builder.py & radar_geometry_parser.py: The 2D/3D spatial verification engines for radar beam coverage.

-   uscrn_scraper.py: Automated fetching of live rural background temperatures.

-   config.json: The central registry for Urban Heat Island modifiers and specific reporting target coordinates.

This updated `README.md` is designed to be professional, documentation-ready for a GitHub repository, and clear about the dual-entry architecture (Streamlit for desktop/Android, CLI for iOS).

You can copy the content below directly into your `README.md` file.

Basic Aviation Knowledge Engine
===============================

The **Basic Aviation Knowledge Engine** is an extensible Python-based suite designed for atmospheric modeling, climatological reporting, and aviation performance calculation. The system is architecture-agnostic, designed to run on desktop environments, Android (via Pydroid), and iOS (via Pyto).

Architecture
---------------

This repository is organized into a modular structure where **Primary Engines** (Atmospheric Models) leverage shared **Secondary Engines** (Physics & Telemetry) to ensure consistent, FAA-aligned calculations.

### Dual-UI Entry Points

The system is built to support two distinct operational environments:

1.  **Dashboard Mode (`app.py`):** A full-featured web interface using **Streamlit**.

    -   *Best for:* Desktop browsers and Android tablets.

    -   *Launch:* `streamlit run app.py`

2.  **iOS/Pyto Mode (`cli_main.py`):** A streamlined Command Line Interface (CLI).

    -   *Best for:* iPad and iPhone portability.

    -   *Launch:* Run `cli_main.py` within the Pyto app.

Project Structure
--------------------

The repository strictly uses `snake_case` filenames (e.g., `sfo_model.py`) to ensure cross-platform import compatibility.

-   **Primary Engines:** `aita_model.py`, `sfo_model.py`, `sea_model.py`, `rossby_model.py`, `aviation_icing.py`, etc.

-   **Secondary Dependencies:** `aviation_physics.py`, `aircraft_perf.py`, `sensor_thermodynamics.py`, `aerodynamic_matrix.py`.

-   **Utilities:** `ai_pirep.py` (Text-to-Speech reporting) and `live_telemetry.py` (Cross-platform sensor integration).

Installation
---------------

Ensure you have the required dependencies installed:

Bash

```
pip install -r requirements.txt

```

Professional & Academic Dedication
-------------------------------------
[Basic Aviation Knowledge Certificate](https://www.parchment.com/u/award/3f309d576264c3d5183346a1eb518282/file)
![Basic Aviation Knowledge](https://seattledatarecovery.com/images/Basic-Aviation-Knowledge.png)
This project is dedicated to the instructors at Green River College, whose guidance provided the framework for this aviation modeling architecture.

-   **Academic Partner:** [Green River College Aviation Technology](https://www.greenriver.edu/students/academics/areas-of-interest/program-maps/trades-industrial-tech-aviation-natural-resources/aviation-technology/index.html)

-   **Professional Reference:** [Fox Rothschild Aviation Practice](https://www.foxrothschild.com/aviation)

PIREP Submission
-------------------

This repository includes an **AI-Assisted PIREP** module (`ai_pirep.py`). This utility generates FAA-standardized PIREP strings based on live flight data for electronic submission to the Aviation Weather Center, with a non-abbreviated text-to-speech output for radio transmission.

> "A PIREP reporting good weather (often called a null report) is just as important to the forecast process as a PIREP reporting poor weather conditions."

License
----------

This repository is managed under the terms of the included [LICENSE](https://www.google.com/search?q=LICENSE&authuser=1) file.

### A Quick Note on the README Update:

-   **Naming Conventions:** I have updated the documentation to emphasize the `snake_case` (underscore) naming, which is vital for Python import stability.

-   **Dual-Controller clarity:** I clearly separated the "Dashboard" vs "CLI" launch instructions, which will save you time when you switch between your PC and your iPad.

-   **Professional Standards:** By including the academic and legal references in the README, you ensure that the repository carries the professional weight expected for aviation-related tooling.

*Derived from metrics aligned with standard Aviation Weather operational requirements.*


