import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SL_API_KEY = os.getenv("SL_API_KEY")
BASE_URL = "https://api.sl.se/api2/realtimedeparturesV4.json"

# Site ID for T-Centralen is 9001
SITE_ID = 9001

def fetch_departures(site_id: int):
    if not SL_API_KEY:
        raise ValueError("SL_API_KEY is not set in the .env file")

    params = {
        "key": SL_API_KEY,
        "siteid": site_id,
        "timewindow": 30, # Look ahead 30 minutes
        "Bus": "false",
        "Train": "false",
        "Tram": "false",
        "Ship": "false",
        "Metro": "true" # Only fetch Metro departures
    }

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("StatusCode") == 0:
            return data["ResponseData"]["Metros"]
        else:
            print(f"API Error: {data.get('Message')}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return []

if __name__ == "__main__":
    print(f"Fetching Metro departures for site {SITE_ID} (T-Centralen)...")
    departures = fetch_departures(SITE_ID)
    
    for dep in departures[:5]: # Print first 5 departures
        line = dep.get("LineNumber")
        destination = dep.get("Destination")
        display_time = dep.get("DisplayTime")
        expected = dep.get("ExpectedDateTime")
        
        print(f"Line {line} to {destination} - {display_time} (Expected: {expected})")
