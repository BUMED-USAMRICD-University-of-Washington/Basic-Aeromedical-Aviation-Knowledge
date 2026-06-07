import json

def export_flight_data(data_dict, filename="flight_out.json"):
    with open(filename, "w") as f:
        json.dump(data_dict, f)
