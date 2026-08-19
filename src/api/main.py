import os
import pickle
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="SL Metro Delay Predictor",
    description="API for predicting SL Metro delays using real-time and historical data",
    version="0.1.0"
)

# Enable CORS for the frontend website
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (update with OCI web server IP in prod)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = None

class PredictionRequest(BaseModel):
    route_id: str
    stop_id: str

@app.on_event("startup")
async def load_model():
    global model
    model_path = "models/baseline_delay_model.pkl"
    if os.path.exists(model_path):
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        print("Baseline model loaded successfully.")
    else:
        print("Warning: Model file not found. API will return default delays.")
        model = {"default_delay": 0}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/predict")
def predict_delay(req: PredictionRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
        
    route_id = req.route_id
    stop_id = req.stop_id
    
    # Simple heuristic lookup
    predicted_delay = model.get("default_delay", 0)
    
    if route_id in model:
        if stop_id in model[route_id]:
            predicted_delay = model[route_id][stop_id]
            
    return {
        "route_id": route_id,
        "stop_id": stop_id,
        "predicted_delay_seconds": round(predicted_delay, 1),
        "status": "delayed" if predicted_delay > 60 else "on_time"
    }

@app.get("/status")
def get_all_routes_status():
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    route_statuses = []
    # Skip the "default_delay" key
    for route_id, stops in model.items():
        if route_id == "default_delay":
            continue
            
        # Calculate the average delay across all stops for this route
        delays = list(stops.values())
        avg_delay = sum(delays) / len(delays) if delays else 0
        
        # Determine a color based on the line number (heuristics for Stockholm)
        color = "bg-slate-500"
        if route_id in ['17', '18', '19']: color = "bg-green-500"
        elif route_id in ['13', '14']: color = "bg-red-500"
        elif route_id in ['10', '11']: color = "bg-blue-500"
        elif route_id in ['40', '41', '42X', '43', '44']: color = "bg-pink-500"
        elif route_id in ['7', '12', '21', '22']: color = "bg-yellow-500" # Trams
        elif len(route_id) <= 3: color = "bg-rose-600" # Buses
        
        route_statuses.append({
            "route_id": route_id,
            "name": f"Line {route_id}",
            "color": color,
            "predicted_delay_seconds": round(avg_delay, 1),
            "status": "delayed" if avg_delay > 60 else "on_time"
        })
        
    # Sort by route ID length, then alphabetically to group similar lines
    route_statuses.sort(key=lambda x: (len(x["route_id"]), x["route_id"]))
    return {"routes": route_statuses}

if __name__ == "__main__":
    import uvicorn
    # Run the server locally
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
