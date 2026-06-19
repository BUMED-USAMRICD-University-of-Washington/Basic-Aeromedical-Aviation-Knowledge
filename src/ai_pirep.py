import pyttsx3 # Standard light Python Text-To-Speech engine

def broadcast_atc_holding_clearance(telemetry_output, tail_number="N732RC"):
    """Generates an audible radio transmission matching standard FAA ATC phraseology."""
    airport = telemetry_output["airport"]
    runway = telemetry_output["selected_runway_side"]
    entry_type = telemetry_output["resolved_pattern_type"]
    heading = int(telemetry_output["landing_magnetic_heading"])
    
    # Format individual digits for ATC realism (e.g., Three Four Zero instead of 340)
    heading_spoken = " ".join(list(str(heading)))
    
    script = (
        f"Skyhawk {tail_number}, ATC clearance received. Proceed directly to the {airport} "
        f"runway threshold fix. Execute a standard {entry_type} entry pattern. "
        f"Expect the {runway} approach. Inbound course heading is {heading_spoken} degrees."
    )
    
    # Initialize vocalization thread
    engine = pyttsx3.init()
    engine.setProperty('rate', 165)  # Realistic rapid radio cadence 
    engine.setProperty('volume', 0.9)
    
    print(f"[RADIO BROADCAST]: {script}")
    engine.say(script)
    engine.runAndWait()
