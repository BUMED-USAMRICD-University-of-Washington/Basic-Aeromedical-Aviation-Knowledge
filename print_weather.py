import socket
from datetime import datetime
try:
    import cupy as np  # Attempt to use GPU-accelerated array math
    print("NVIDIA GPU Acceleration Engaged")
except ImportError:
    import numpy as np # Fallback to standard CPU math
    print("Using CPU (NVIDIA acceleration not detected)")
def format_aviation_printout(icao_station, metar_data, taf_data, pireps):
    """
    Formats raw weather text data into a structured, easily readable slip.
    Uses fixed-width formatting to ensure perfect vertical alignment.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    print_job = []
    print_job.append("==========================================")
    print_job.append(f"          AVIATION WEATHER BRIEF          ")
    print_job.append(f"          STATION: {icao_station.upper()}              ")
    print_job.append(f"          PRINTED: {timestamp}        ")
    print_job.append("==========================================")
    print_job.append("\n[CURRENT METAR]")
    print_job.append(metar_data)
    print_job.append("\n[WEATHER PREDICTIONS / TAF]")
    for line in taf_data.split('\n'):
        print_job.append(line)
    print_job.append("\n[PILOT REPORTS / PIREPS]")
    if pireps:
        for idx, pirep in enumerate(pireps, 1):
            print_job.append(f"Report {idx}:")
            print_job.append(pirep)
            print_job.append("-" * 30)
    else:
        print_job.append("NO ACTIVE PIREPS REPORTED FOR THIS AREA.")
    print_job.append("\n\n==========================================")
    print_job.append("             END OF BRIEFING              ")
    print_job.append("==========================================\n\n\n\n")
    return "\n".join(print_job)
def send_to_network_printer(ip_address, text_payload):
    """Sends the raw formatted text string directly over network port 9100."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((ip_address, 9100))
            # Convert text string to raw bytes using standard UTF-8 or ASCII
            s.sendall(text_payload.encode('utf-8'))
        print("Weather briefing dispatched to printer successfully.")
    except Exception as e:
        print(f"Printing failed: {e}")
station = "KJFK"
metar = "KJFK 070851Z 11006KT 10SM FEW045 BKN250 18/14 A3002 RMK AO2 SLP164"
taf = """KJFK 070550Z 0706/0812 13007KT P6SM SKC
FM071400 16011KT P6SM FEW050
FM080100 17008KT P6SM BKN060"""
pirep_list = [
    "UA /OV JFK045015 /TM 0830 /FL060 /TP B738 /TA M02 /WV 12015KT /TB LGT",
    "UUA /OV LGA /TM 0842 /FL020 /TP A320 /LLWS -15KT SFC-020 BY ARRIVING ACFT"
]
formatted_briefing = format_aviation_printout(station, metar, taf, pirep_list)
send_to_network_printer("192.168.1.150", formatted_briefing)
