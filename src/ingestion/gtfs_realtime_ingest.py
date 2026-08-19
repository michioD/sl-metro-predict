import os
import requests
from dotenv import load_dotenv

load_dotenv()

def fetch_gtfs_realtime():
    """
    Fetches the GTFS Sweden 3 Realtime data from Trafiklab.
    """
    api_key = os.getenv("TRAFIKLAB_API_KEY")
    if not api_key:
        raise ValueError("TRAFIKLAB_API_KEY environment variable is not set")
        
    url = f"https://opendata.samtrafiken.se/gtfs-rt-sweden/sl/TripUpdates.pb?key={api_key}"
    
    print(f"Fetching data from: {url.replace(api_key, '***')}")
    response = requests.get(url)
    
    if response.status_code == 200:
        print(f"Successfully downloaded {len(response.content)} bytes of GTFS Realtime data.")
        # We would typically save this to MinIO Bronze layer here
        with open("data/raw/TripUpdates.pb", "wb") as f:
            f.write(response.content)
    else:
        print(f"Failed to fetch data: HTTP {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # Ensure data/raw directory exists
    os.makedirs("data/raw", exist_ok=True)
    fetch_gtfs_realtime()
