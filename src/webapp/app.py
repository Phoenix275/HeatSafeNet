"""
FastAPI web application for HeatSafeNet.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os
import geopandas as gpd
import numpy as np
from pathlib import Path

# Import our solver
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from model.mclp_solver import MCLPSolver


app = FastAPI(
    title="HeatSafeNet API",
    description="Optimize cooling and connectivity resilience hubs for extreme heat",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "frontend"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# Pydantic models
class SolveRequest(BaseModel):
    city: str
    K: int = 10
    mode: str = "walk"  # "walk" or "drive"
    weights: Dict[str, float] = {
        "heat_exposure": 0.35,
        "social_vulnerability": 0.30,
        "digital_exclusion": 0.25,
        "elderly_vulnerability": 0.10
    }


class SiteInfo(BaseModel):
    site_id: int
    name: str
    amenity: str
    coordinates: Dict[str, float]
    catchment_stats: Dict[str, float]


class SolveResponse(BaseModel):
    selected_sites: List[SiteInfo]
    summary_stats: Dict[str, float]
    solution_metadata: Dict[str, str]


# Global data cache
data_cache = {
    "cbg_data": {},
    "candidate_data": {},
    "coverage_data": {},
    "initialized": False
}


def initialize_data():
    """Load data on startup."""
    if data_cache["initialized"]:
        return
        
    print("Initializing data cache...")
    
    # Load CBG data with risk index
    cbg_path = "data/out/cbg_with_risk_index.geojson"
    if os.path.exists(cbg_path):
        cbg_gdf = gpd.read_file(cbg_path)
        
        # Convert to city-based structure
        for county_name in cbg_gdf["county_name"].unique():
            city_key = county_name.replace(" County", "").replace(", TX", "").replace(", AZ", "")
            county_data = cbg_gdf[cbg_gdf["county_name"] == county_name]
            
            # Convert to GeoJSON format for API
            geojson_data = json.loads(county_data.to_json())
            data_cache["cbg_data"][city_key] = geojson_data
            
    # Load candidate sites
    candidates_path = "data/int/candidate_sites.geojson"
    if os.path.exists(candidates_path):
        candidates_gdf = gpd.read_file(candidates_path)
        
        for county_name in candidates_gdf["county_name"].unique():
            city_key = county_name.replace(" County", "").replace(", TX", "").replace(", AZ", "")
            county_data = candidates_gdf[candidates_gdf["county_name"] == county_name]
            
            geojson_data = json.loads(county_data.to_json())
            data_cache["candidate_data"][city_key] = geojson_data
            
    # Load coverage data
    coverage_dir = "data/int"
    if os.path.exists(coverage_dir):
        for filename in os.listdir(coverage_dir):
            if filename.startswith("coverage_") and filename.endswith(".json"):
                filepath = os.path.join(coverage_dir, filename)
                
                with open(filepath, 'r') as f:
                    coverage_data = json.load(f)
                    
                # Extract city name
                if "Harris_County_TX" in filename:
                    city_key = "Harris"
                elif "Maricopa_County_AZ" in filename:
                    city_key = "Maricopa"
                else:
                    city_key = filename.replace("coverage_", "").replace(".json", "")
                    
                data_cache["coverage_data"][city_key] = coverage_data
                
    data_cache["initialized"] = True
    print(f"Data cache initialized: {len(data_cache['cbg_data'])} cities")


@app.on_event("startup")
async def startup_event():
    """Initialize data on startup."""
    initialize_data()


@app.get("/")
async def root():
    """Serve the main application page."""
    html_path = Path(__file__).parent / "frontend" / "index.html"
    
    if html_path.exists():
        with open(html_path, 'r') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    else:
        return HTMLResponse(content="""
        <html>
            <head><title>HeatSafeNet</title></head>
            <body>
                <h1>HeatSafeNet API</h1>
                <p>API is running. Frontend not yet deployed.</p>
                <p>Available endpoints:</p>
                <ul>
                    <li><a href="/docs">API Documentation</a></li>
                    <li><a href="/cities">Available Cities</a></li>
                    <li><a href="/risk/Harris">Risk Data (Harris)</a></li>
                </ul>
            </body>
        </html>
        """)


@app.get("/cities")
async def get_available_cities():
    """Get list of available cities."""
    initialize_data()
    
    cities = []
    for city_key in data_cache["cbg_data"].keys():
        city_info = {
            "key": city_key,
            "name": city_key + " County",
            "has_cbg_data": city_key in data_cache["cbg_data"],
            "has_candidate_data": city_key in data_cache["candidate_data"],
            "has_coverage_data": city_key in data_cache["coverage_data"]
        }
        cities.append(city_info)
        
    return {"cities": cities}


@app.get("/risk/{city}")
async def get_risk_data(city: str):
    """Get risk index data for a city."""
    initialize_data()
    
    if city not in data_cache["cbg_data"]:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")
        
    return data_cache["cbg_data"][city]


@app.get("/candidates/{city}")
async def get_candidates(city: str):
    """Get candidate sites for a city."""
    initialize_data()
    
    if city not in data_cache["candidate_data"]:
        raise HTTPException(status_code=404, detail=f"Candidates for city '{city}' not found")
        
    return data_cache["candidate_data"][city]


@app.post("/solve")
async def solve_optimization(request: SolveRequest):
    """Solve MCLP optimization problem."""
    initialize_data()
    
    # Validate inputs
    if request.city not in data_cache["coverage_data"]:
        raise HTTPException(
            status_code=404, 
            detail=f"Coverage data for city '{request.city}' not found"
        )
        
    if request.mode not in ["walk", "drive"]:
        raise HTTPException(
            status_code=400,
            detail="Mode must be 'walk' or 'drive'"
        )
        
    if not (1 <= request.K <= 50):
        raise HTTPException(
            status_code=400,
            detail="K must be between 1 and 50"
        )
        
    # Validate weights sum to 1
    weight_sum = sum(request.weights.values())
    if not np.isclose(weight_sum, 1.0, rtol=1e-3):
        raise HTTPException(
            status_code=400,
            detail=f"Weights must sum to 1.0, got {weight_sum:.3f}"
        )
        
    try:
        # Get coverage data
        coverage_data = data_cache["coverage_data"][request.city]
        
        if request.mode not in coverage_data:
            raise HTTPException(
                status_code=400,
                detail=f"Mode '{request.mode}' not available for city '{request.city}'"
            )
            
        mode_data = coverage_data[request.mode]
        
        # If weights are different from default, need to recompute demand weights
        demand_weights = mode_data["demand_metadata"]["demand_weights"]
        
        # Check if we need to recompute weights
        default_weights = {
            "heat_exposure": 0.35,
            "social_vulnerability": 0.30, 
            "digital_exclusion": 0.25,
            "elderly_vulnerability": 0.10
        }
        
        if request.weights != default_weights:
            # Would need access to component data to recompute
            # For now, use existing weights with a warning
            print(f"Warning: Custom weights requested but using precomputed demand weights")
            
        # Solve optimization
        solver = MCLPSolver()
        
        selected_sites, objective_value, solution_info = solver.solve_mclp(
            mode_data["coverage_matrix"],
            demand_weights,
            request.K
        )
        
        # Prepare response with site details
        site_info_list = []
        supply_metadata = mode_data["supply_metadata"]
        
        for site_idx in selected_sites:
            if site_idx < len(supply_metadata["site_ids"]):
                # Get site metadata
                site_info = SiteInfo(
                    site_id=site_idx,
                    name=supply_metadata["site_names"][site_idx],
                    amenity=supply_metadata["amenity_types"][site_idx],
                    coordinates={
                        "lat": 0.0,  # Would need to look up from candidates data
                        "lon": 0.0
                    },
                    catchment_stats={
                        "covered_demand_weight": 0.0,  # Would compute from coverage matrix
                        "covered_population": 0
                    }
                )
                site_info_list.append(site_info)
                
        # Summary statistics
        total_demand = len(demand_weights)
        covered_demand = solution_info.get("covered_demand_points", 0)
        
        summary_stats = {
            "sites_selected": len(selected_sites),
            "covered_demand_points": covered_demand,
            "total_demand_points": total_demand,
            "coverage_rate": covered_demand / total_demand if total_demand > 0 else 0,
            "total_covered_weight": solution_info.get("total_covered_weight", 0),
            "objective_value": objective_value
        }
        
        response = SolveResponse(
            selected_sites=site_info_list,
            summary_stats=summary_stats,
            solution_metadata={
                "solver_status": solution_info.get("status", "unknown"),
                "solve_time_sec": str(solution_info.get("solve_time_sec", 0)),
                "city": request.city,
                "mode": request.mode,
                "K": str(request.K)
            }
        )
        
        return response
        
    except Exception as e:
        print(f"Error in optimization: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Optimization failed: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    initialize_data()
    
    return {
        "status": "healthy",
        "data_initialized": data_cache["initialized"],
        "available_cities": list(data_cache["cbg_data"].keys())
    }


@app.get("/stats/{city}")
async def get_city_stats(city: str):
    """Get summary statistics for a city."""
    initialize_data()
    
    if city not in data_cache["cbg_data"]:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")
        
    cbg_data = data_cache["cbg_data"][city]
    features = cbg_data["features"]
    
    # Calculate statistics
    risk_scores = [f["properties"]["risk"] for f in features if "risk" in f["properties"]]
    populations = [f["properties"].get("total_population", 0) for f in features]
    
    stats = {
        "total_block_groups": len(features),
        "total_population": sum(populations),
        "risk_statistics": {
            "mean": np.mean(risk_scores) if risk_scores else 0,
            "std": np.std(risk_scores) if risk_scores else 0,
            "min": min(risk_scores) if risk_scores else 0,
            "max": max(risk_scores) if risk_scores else 0,
            "high_risk_count": sum(1 for r in risk_scores if r > 0.75)
        },
        "candidate_sites": len(data_cache["candidate_data"].get(city, {}).get("features", [])),
        "coverage_scenarios": list(data_cache["coverage_data"].get(city, {}).keys())
    }
    
    return stats


if __name__ == "__main__":
    import uvicorn
    
    print("Starting HeatSafeNet API server...")
    
    # In development, run with auto-reload
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["src"]
    )