import os
import zipfile
import pandas as pd
from google.transit import gtfs_realtime_pb2
import pickle

def extract_static_gtfs(zip_path, extract_to="data/raw/static"):
    """Extract necessary files from the GTFS static zip."""
    print("Extracting GTFS static data...")
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file in ["routes.txt", "stops.txt", "trips.txt"]:
            try:
                zip_ref.extract(file, extract_to)
                print(f"Extracted {file}")
            except KeyError:
                print(f"Warning: {file} not found in zip.")

def parse_realtime_data(pb_path):
    """Parse GTFS Realtime protobuf into a pandas DataFrame."""
    print("Parsing GTFS Realtime data...")
    feed = gtfs_realtime_pb2.FeedMessage()
    with open(pb_path, "rb") as f:
        feed.ParseFromString(f.read())
        
    records = []
    for entity in feed.entity:
        if entity.HasField('trip_update'):
            trip_id = entity.trip_update.trip.trip_id
            route_id = entity.trip_update.trip.route_id
            for stop_time_update in entity.trip_update.stop_time_update:
                stop_id = stop_time_update.stop_id
                delay = None
                if stop_time_update.HasField('arrival') and stop_time_update.arrival.HasField('delay'):
                    delay = stop_time_update.arrival.delay
                elif stop_time_update.HasField('departure') and stop_time_update.departure.HasField('delay'):
                    delay = stop_time_update.departure.delay
                
                if delay is not None:
                    records.append({
                        "trip_id": trip_id,
                        "rt_route_id": route_id,
                        "stop_id": stop_id,
                        "delay_seconds": delay
                    })
    df = pd.DataFrame(records)
    print(f"Parsed {len(df)} real-time delay records.")
    return df

def build_baseline_model():
    """Build a simple baseline model using average historical delays."""
    static_dir = "data/raw/static"
    pb_path = "data/raw/TripUpdates.pb"
    zip_path = "data/raw/gtfs_static_sweden.zip"
    
    if not os.path.exists(f"{static_dir}/routes.txt") or not os.path.exists(f"{static_dir}/trips.txt"):
        extract_static_gtfs(zip_path, static_dir)
        
    # Load static data
    print("Loading static data...")
    routes_df = pd.read_csv(f"{static_dir}/routes.txt", dtype=str)
    stops_df = pd.read_csv(f"{static_dir}/stops.txt", dtype=str)
    trips_df = pd.read_csv(f"{static_dir}/trips.txt", dtype=str)
    
    # Parse real-time
    rt_df = parse_realtime_data(pb_path)
    
    if rt_df.empty:
        print("No delay data found in real-time feed. Using fallback defaults.")
        delay_model = {"default_delay": 0}
    else:
        # Many GTFS RT feeds omit route_id, so we must join on trip_id first
        print("Joining with trips.txt to resolve route_id...")
        df = rt_df.merge(trips_df[['trip_id', 'route_id']], on='trip_id', how='left')
        
        # Now join with routes.txt to get the short name (e.g., '17', '13')
        print("Joining with routes.txt to resolve route_short_name...")
        df = df.merge(routes_df[['route_id', 'route_short_name']], on='route_id', how='left')
        
        # Build heuristic model: average delay per route_short_name and stop_id
        # We drop any NaNs where we couldn't resolve the route
        df_clean = df.dropna(subset=['route_short_name'])
        
        avg_delays = df_clean.groupby(['route_short_name', 'stop_id'])['delay_seconds'].mean().reset_index()
        
        # Convert to dictionary for fast lookup in API
        delay_model = {}
        for _, row in avg_delays.iterrows():
            r_id = str(row['route_short_name'])
            s_id = str(row['stop_id'])
            if r_id not in delay_model:
                delay_model[r_id] = {}
            delay_model[r_id][s_id] = float(row['delay_seconds'])
            
        delay_model["default_delay"] = float(rt_df['delay_seconds'].mean())
        print(f"Model keys successfully mapped to route_short_names: {list(delay_model.keys())[:10]}")
        
    # Save the model
    os.makedirs("models", exist_ok=True)
    with open("models/baseline_delay_model.pkl", "wb") as f:
        pickle.dump(delay_model, f)
    
    print("Baseline model trained and saved to models/baseline_delay_model.pkl")

if __name__ == "__main__":
    build_baseline_model()
