#!/usr/bin/env python3
"""
Create demo data for HeatSafeNet web interface.
"""
import os
import json
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, Polygon
import pandas as pd

def create_demo_data():
    """Create minimal demo data for the web interface."""
    
    # Create directories
    os.makedirs("data/out", exist_ok=True)
    os.makedirs("data/int", exist_ok=True)
    
    print("Creating demo data for HeatSafeNet...")
    
    # Create sample block groups for Houston
    houston_bounds = (-95.8, 29.5, -95.0, 30.1)  # west, south, east, north
    houston_cbgs = create_sample_cbgs("Harris County, TX", houston_bounds, "48201")
    
    # Create sample block groups for Phoenix  
    phoenix_bounds = (-112.8, 33.2, -111.6, 33.9)
    phoenix_cbgs = create_sample_cbgs("Maricopa County, AZ", phoenix_bounds, "04013")
    
    # Combine CBGs
    all_cbgs = pd.concat([houston_cbgs, phoenix_cbgs], ignore_index=True)
    
    # Save CBG data with risk index
    print("Saving CBG risk data...")
    all_cbgs.to_file("data/out/cbg_with_risk_index.geojson", driver="GeoJSON")
    
    # Create candidate sites
    houston_candidates = create_sample_candidates("Harris County, TX", houston_bounds)
    phoenix_candidates = create_sample_candidates("Maricopa County, AZ", phoenix_bounds)
    
    all_candidates = pd.concat([houston_candidates, phoenix_candidates], ignore_index=True)
    
    print("Saving candidate sites...")
    all_candidates.to_file("data/int/candidate_sites.geojson", driver="GeoJSON")
    
    # Create sample coverage data
    create_sample_coverage_data()
    
    print("✅ Demo data created successfully!")
    print("Files created:")
    print("  - data/out/cbg_with_risk_index.geojson")
    print("  - data/int/candidate_sites.geojson") 
    print("  - data/int/coverage_Harris_County_TX.json")
    print("  - data/int/coverage_Maricopa_County_AZ.json")

def create_sample_cbgs(county_name, bounds, county_fips):
    """Create sample census block groups."""
    west, south, east, north = bounds
    
    # Create a 10x10 grid of block groups
    n_x, n_y = 10, 10
    
    geometries = []
    data = []
    
    np.random.seed(42)  # For reproducible demo data
    
    for i in range(n_x):
        for j in range(n_y):
            # Grid cell bounds
            x1 = west + i * (east - west) / n_x
            x2 = west + (i + 1) * (east - west) / n_x
            y1 = south + j * (north - south) / n_y  
            y2 = south + (j + 1) * (north - south) / n_y
            
            # Create polygon
            poly = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
            geometries.append(poly)
            
            # Generate sample data
            geoid = f"{county_fips}{i:03d}{j:03d}{1}"  # Simplified GEOID
            
            # Generate realistic risk components
            heat_exposure = np.random.beta(2, 2)  # 0-1 scale
            social_vulnerability = np.random.beta(2, 3) 
            digital_exclusion = np.random.beta(2, 3)
            elderly_vulnerability = np.random.beta(2, 4)
            
            # Compute composite risk
            risk = (0.35 * heat_exposure + 
                   0.30 * social_vulnerability + 
                   0.25 * digital_exclusion + 
                   0.10 * elderly_vulnerability)
            
            # Generate population
            population = int(np.random.uniform(500, 2000))
            
            data.append({
                "GEOID": geoid,
                "county_name": county_name,
                "total_population": population,
                "heat_exposure": heat_exposure,
                "social_vulnerability": social_vulnerability, 
                "digital_exclusion": digital_exclusion,
                "elderly_vulnerability": elderly_vulnerability,
                "risk": risk,
                "demand_weight": risk * population,
                "pct_65_plus": np.random.uniform(10, 35),
                "pct_poverty": np.random.uniform(5, 40),
                "pct_no_internet": np.random.uniform(5, 30)
            })
    
    return gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")

def create_sample_candidates(county_name, bounds):
    """Create sample candidate sites."""
    west, south, east, north = bounds
    
    np.random.seed(42)
    n_sites = 25
    
    amenities = ["school", "library", "community_centre", "place_of_worship", "hospital"]
    amenity_weights = [0.4, 0.2, 0.2, 0.15, 0.05]
    
    geometries = []
    data = []
    
    for i in range(n_sites):
        # Random location
        lon = np.random.uniform(west, east)
        lat = np.random.uniform(south, north)
        
        point = Point(lon, lat)
        geometries.append(point)
        
        # Random amenity type
        amenity = np.random.choice(amenities, p=amenity_weights)
        
        # Generate name
        name_parts = {
            "school": ["Elementary", "Middle", "High", "Charter"],
            "library": ["Public", "Branch", "Community", "Central"], 
            "community_centre": ["Community", "Recreation", "Senior", "Youth"],
            "place_of_worship": ["First", "Saint", "Mount", "Trinity"],
            "hospital": ["General", "Medical", "Regional", "Community"]
        }
        
        prefix = np.random.choice(name_parts[amenity])
        name = f"{prefix} {amenity.replace('_', ' ').title()}"
        
        data.append({
            "name": name,
            "amenity": amenity,
            "county_name": county_name,
            "addr_street": f"{np.random.randint(100, 9999)} Main St",
            "footprint_area_m2": np.random.uniform(500, 3000)
        })
    
    return gpd.GeoDataFrame(data, geometry=geometries, crs="EPSG:4326")

def create_sample_coverage_data():
    """Create sample coverage matrices for optimization."""
    
    # Create simplified coverage data for both counties
    counties = [
        ("Harris_County_TX", "Harris County, TX"),
        ("Maricopa_County_AZ", "Maricopa County, AZ")
    ]
    
    for county_file, county_name in counties:
        # Create mock coverage data
        n_demand = 100  # 100 block groups
        n_supply = 25   # 25 candidate sites
        
        # Create coverage matrix (which sites can serve which demand points)
        np.random.seed(42)
        coverage_matrix = {}
        
        for i in range(n_demand):
            # Each demand point can be served by 3-8 sites on average
            n_covering = np.random.randint(3, 9)
            covering_sites = np.random.choice(n_supply, size=n_covering, replace=False).tolist()
            coverage_matrix[str(i)] = covering_sites
        
        # Create demand metadata
        demand_weights = np.random.uniform(100, 2000, n_demand).tolist()
        risk_scores = np.random.beta(2, 2, n_demand).tolist()
        geoids = [f"48201{i:06d}1" for i in range(n_demand)]
        
        # Create supply metadata  
        site_names = [f"Site {i+1}" for i in range(n_supply)]
        amenity_types = np.random.choice(
            ["school", "library", "community_centre", "place_of_worship"], 
            size=n_supply
        ).tolist()
        footprint_areas = np.random.uniform(500, 3000, n_supply).tolist()
        
        # Create coverage data structure
        coverage_data = {
            "walk": {
                "coverage_matrix": coverage_matrix,
                "demand_metadata": {
                    "geoids": geoids,
                    "demand_weights": demand_weights,
                    "risk_scores": risk_scores,
                    "network_nodes": list(range(n_demand))
                },
                "supply_metadata": {
                    "site_ids": list(range(n_supply)),
                    "amenity_types": amenity_types,
                    "site_names": site_names,
                    "footprint_areas": footprint_areas,
                    "network_nodes": list(range(n_supply))
                },
                "network_stats": {
                    "nodes": 500,
                    "edges": 1200,
                    "max_travel_time_min": 10
                }
            },
            "drive": {
                "coverage_matrix": coverage_matrix,
                "demand_metadata": {
                    "geoids": geoids,
                    "demand_weights": demand_weights,
                    "risk_scores": risk_scores,
                    "network_nodes": list(range(n_demand))
                },
                "supply_metadata": {
                    "site_ids": list(range(n_supply)),
                    "amenity_types": amenity_types,
                    "site_names": site_names,
                    "footprint_areas": footprint_areas,
                    "network_nodes": list(range(n_supply))
                },
                "network_stats": {
                    "nodes": 500,
                    "edges": 1200,
                    "max_travel_time_min": 10
                }
            }
        }
        
        # Save coverage data
        output_path = f"data/int/coverage_{county_file}.json"
        with open(output_path, 'w') as f:
            json.dump(coverage_data, f, indent=2)

if __name__ == "__main__":
    create_demo_data()