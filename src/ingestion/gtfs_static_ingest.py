import os
import requests
from dotenv import load_dotenv

load_dotenv()

def fetch_gtfs_static():
    """
    Fetches the GTFS Sweden 3 Static data from Trafiklab.
    This contains the timetables, stop locations, and route definitions.
    """
    api_key = os.getenv("TRAFIKLAB_STATIC_API_KEY")
    if not api_key:
        raise ValueError("TRAFIKLAB_STATIC_API_KEY environment variable is not set")
        
    url = f"https://opendata.samtrafiken.se/gtfs-sweden/sweden.zip?key={api_key}"
    
    print(f"Fetching static data from: {url.replace(api_key, '***')}")
    # Use stream=True for large files like GTFS static zip
    with requests.get(url, stream=True) as response:
        if response.status_code == 200:
            file_path = "data/raw/gtfs_static_sweden.zip"
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Successfully downloaded GTFS Static data to {file_path}.")
        else:
            print(f"Failed to fetch data: HTTP {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)
    fetch_gtfs_static()
