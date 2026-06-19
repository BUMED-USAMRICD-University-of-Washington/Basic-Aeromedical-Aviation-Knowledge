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
    
import pyttsx3

def verbalize_copilot_fuel_announcement(endurance_minutes, fuel_flow_pph, bingo_threshold, is_critical=False):
    """Generates an immediate audio broadcast using realistic operational phraseology."""
    engine = pyttsx3.init()
    engine.setProperty('rate', 170)  # Professional cockpit cadence
    engine.setProperty('volume', 0.95)
    
    mins = int(endurance_minutes)
    flow = int(fuel_flow_pph)
    bingo = int(bingo_threshold)

    if is_critical or mins <= 5:
        speech_script = (
            f"Captain, advisory notice. Usable hold fuel is depleted. Fuel flow is {flow} pounds per hour. "
            f"We have reached our bingo threshold of {bingo} pounds. Request immediate exit from the holding pattern "
            f"and divert to our alternate airport."
        )
        print(f"\n[AUDIO WARNING]: {speech_script}")
    else:
        speech_script = (
            f"Holding pattern stabilized. Fuel flow checked at {flow} pounds per hour. "
            f"We have exactly {mins} minutes of remaining hold endurance before hitting our bingo limit of {bingo} pounds."
        )
        print(f"\n[AUDIO BROADCAST]: {speech_script}")
        
    engine.say(speech_script)
    engine.runAndWait()
