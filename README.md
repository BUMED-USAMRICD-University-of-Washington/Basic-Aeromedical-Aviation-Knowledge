# Basic Aviation Knowledge - Airport Reporting Models

## Overview
This repository contains predictive mathematical models and Python scripts designed **ONLY to predict Climatological Report temperatures** for major airports. 

These models are not designed to track real-time, transient flight-deck or runway conditions. Instead, they project the absolute maximum 24-hour temperature achieved at specific verified sensors. Knowing the baseline is a critical, life-or-death metric for pilots calculating true Density Altitude, flight performance, and Go/No-Go safety thresholds.

These tools are built for aviation professionals, dispatchers, and airport operations teams on GitHub.

## 📂 Repository Architecture & Equation Mapping

The repository is divided into localized climate models and macro-scale astronomical trackers:

### 1. `SFO-climate-model.py` (San Francisco / KMUX Area)
Predicts the Downtown/Peninsula validation high by calculating Central Valley thermal low compression on the marine inversion layer.

### 2. `LAX-climate-model.py` (Los Angeles / KVTX Area)
Quantifies the precise spatial decay of marine layer stratus from the direct coastline moving inland across the coastal basin.

### 3. `AUS-climate-model.py` (Austin / KGRK Area)
Predicts macro temperature drops caused by multi-cell storm training and localized micro-scale latent heat absorption along the Balcones Escarpment.

### 4. `AITA-spikes.py` (Atlanta / KFFC Area)
Models sudden single-day temperature spikes caused by maritime Bermuda High ridging, dynamic subsidence, and downslope compression over the Appalachian foothills.

### 5. `tidal-temperatures.py`
Formulates the direct microclimate heat flux adjustments at coastal weather stations based on the physical distance to moving shorelines at high tide.

### 6. `luna-tracker.py` & `luna-phase.py`
Accounts for macro-scale atmospheric tidal compression and synodic 29.53-day monthly modulation waves (gravitational vs. thermal albedo components) on base data.

---

## 📖 Unified Data Dictionary & Global Variables

To maintain normalization across all scripts, the repository uses a strict schema. When configuring local constants or a `config.json` file, refer to the following variable definitions:

| Script Parameter | Physics / Meteorological Definition | Alignment Rule |
| :--- | :--- | :--- |
| `\Delta T_{\text{station}}` | Localized spatial sensor offset constant. | Adjusts for the specific microclimatic pocket of the weather station relative to the runway. |
| `\Theta(x)` | Heaviside step function switch ($1$ or $0$). | Activates or dampens localized microclimate triggers based on boundary rules. |
| `\tau_{\text{crit}}` / `\tau` | Physical atmospheric boundary thresholds. | Represents the tipping bounds where the onshore pump stalls or cloud decks hit 100% saturation. |
| `z_{\text{marine}}` / `z_{\text{inv}}` | Height of the marine boundary / inversion layer. | Used to determine rapid fog burn-off windows or coastal lifting limits. |
| `-\vec{V} \cdot \nabla T` | Horizontal Warm Air Advection (WAA) vector. | Determines the thermal injection rate when local winds align with high tropical heat gradients. |
| `H_{\text{tide}}(t)` | Dynamic tidal gauge displacement height over time. | Contracts the physical distance between the cold ocean mass sink and the station sensor. |

## 🚀 Usage

To integrate these models into your flight planning software or airport operations dashboard:
1. Clone the repository.
2. Modify the target Global Variables (e.g., `DELTA_T_STATION`) within the specific script or centralized configuration file to match the physical offset of your target sensor.
3. Pass real-time macro synoptic weather data into the specific location models to generate the final verification target.

---
*Developed utilizing meteorological standards aligned with the FAA Aviation Weather Handbook.*

## Core Dependencies & Architecture

This repository relies on a highly specific stack of mathematical, spatial, and hardware-interfacing Python libraries to process live thermodynamic variables and DGPS telemetry.

* **`streamlit`**: Drives the interactive web dashboard (`app.py`), allowing real-time switching between static planning models and live in-flight telemetry modes.
* **`pandas`**: Parses complex, fixed-width text data from the NOAA USCRN API and processes tabular coordinate exports from ExpertGPS.
* **`numpy`**: Powers the heavy mathematical arrays required for the thermodynamic equations, including urban thermal decay constants and lake breeze frontal boundary limits.
* **`matplotlib`**: Generates the 2D spatial cross-sections and temperature timeline visualizations rendered directly on the Streamlit dashboard.
* **`requests`**: Handles the automated HTTP requests to fetch pristine rural baseline temperatures ($T_{rural}$) for Urban Heat Island calculations.
* **`shapely`**: Constructs the mathematical 2D bounding boxes to verify if a specific coordinate sits inside an active radar footprint.
* **`pyserial`**: Opens the hardware serial ports (COM/tty) to physically interface with USB DGPS and barometric elevation dongles.
* **`pynmea2`**: Decodes the raw `$GPGGA` and `$GNGGA` satellite text strings streaming from the dongle into clean, usable latitude, longitude, and elevation variables.
