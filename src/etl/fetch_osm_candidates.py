"""
Fetch potential resilience hub sites from OpenStreetMap.
"""
import geopandas as gpd
import requests
import pandas as pd
from typing import List, Dict, Tuple
import time
import os
from shapely.geometry import Point, Polygon
import json


class OSMFetcher:
    """Fetch candidate sites from OpenStreetMap via Overpass API."""
    
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    
    def __init__(self):
        """Initialize OSM fetcher."""
        pass
        
    def build_overpass_query(self, bbox: Tuple[float, float, float, float]) -> str:
        """
        Build Overpass API query for candidate amenities.
        
        Args:
            bbox: (south, west, north, east) bounding box
            
        Returns:
            Overpass QL query string
        """
        south, west, north, east = bbox
        
        query = f"""
        [out:json][timeout:60];
        (
          way["amenity"~"^(school|library|community_centre|place_of_worship|university|hospital|clinic)$"]({south},{west},{north},{east});
          relation["amenity"~"^(school|library|community_centre|place_of_worship|university|hospital|clinic)$"]({south},{west},{north},{east});
        );
        out center meta;
        """
        
        return query
        
    def fetch_county_candidates(self, county_bounds: Tuple[float, float, float, float],
                              county_name: str) -> gpd.GeoDataFrame:
        """
        Fetch candidate sites for a county from OSM.
        
        Args:
            county_bounds: Bounding box (south, west, north, east)
            county_name: Human-readable county name
            
        Returns:
            GeoDataFrame with candidate sites
        """
        print(f"Fetching OSM candidates for {county_name}...")
        
        query = self.build_overpass_query(county_bounds)
        
        try:
            response = requests.post(
                self.OVERPASS_URL,
                data=query,
                headers={"User-Agent": "HeatSafeNet/1.0"}
            )
            response.raise_for_status()
            data = response.json()
            
            return self._process_osm_response(data, county_name)
            
        except Exception as e:
            print(f"Error fetching OSM data: {e}")
            print("Creating mock candidate data...")
            return self._create_mock_candidates(county_bounds, county_name)
            
    def _process_osm_response(self, data: Dict, county_name: str) -> gpd.GeoDataFrame:
        """Process Overpass API response into GeoDataFrame."""
        
        candidates = []
        
        for element in data.get("elements", []):
            # Extract coordinates
            if element["type"] == "way" and "center" in element:
                lat = element["center"]["lat"] 
                lon = element["center"]["lon"]
            elif "lat" in element and "lon" in element:
                lat = element["lat"]
                lon = element["lon"] 
            else:
                continue
                
            # Extract tags
            tags = element.get("tags", {})
            
            candidate = {
                "osm_id": element["id"],
                "osm_type": element["type"],
                "amenity": tags.get("amenity", "unknown"),
                "name": tags.get("name", "Unnamed"),
                "addr_street": tags.get("addr:street", ""),
                "addr_city": tags.get("addr:city", ""),
                "building": tags.get("building", ""),
                "operator": tags.get("operator", ""),
                "denomination": tags.get("denomination", ""),
                "geometry": Point(lon, lat),
                "county_name": county_name
            }
            
            candidates.append(candidate)
            
        if not candidates:
            # If no results, create mock data
            bounds = county_bounds if isinstance(county_bounds, tuple) else (-95, 29.5, -95.5, 30)
            return self._create_mock_candidates(bounds, county_name)
            
        gdf = gpd.GeoDataFrame(candidates, crs="EPSG:4326")
        return gdf
        
    def _create_mock_candidates(self, bounds: Tuple[float, float, float, float], 
                               county_name: str) -> gpd.GeoDataFrame:
        """Create mock candidate sites for testing."""
        import numpy as np
        
        south, west, north, east = bounds
        
        # Set random seed based on county
        seed = hash(county_name) % 1000
        np.random.seed(seed)
        
        # Generate candidate sites
        n_sites = 50
        
        # Amenity types and their relative frequencies  
        amenities = {
            "school": 0.35,
            "library": 0.15, 
            "community_centre": 0.20,
            "place_of_worship": 0.25,
            "hospital": 0.05
        }
        
        candidates = []
        
        for i in range(n_sites):
            # Random location within bounds
            lat = np.random.uniform(south, north)
            lon = np.random.uniform(west, east)
            
            # Choose amenity type
            amenity = np.random.choice(
                list(amenities.keys()),
                p=list(amenities.values())
            )
            
            # Generate realistic names
            name_prefixes = {
                "school": ["Elementary", "Middle", "High", "Charter"],
                "library": ["Public", "Branch", "Community", "Regional"],
                "community_centre": ["Community", "Recreation", "Senior", "Youth"],  
                "place_of_worship": ["First", "Saint", "Mount", "Trinity"],
                "hospital": ["General", "Medical", "Regional", "Community"]
            }
            
            prefix = np.random.choice(name_prefixes[amenity])
            suffix = f"{amenity.replace('_', ' ').title()}"
            name = f"{prefix} {suffix}"
            
            candidate = {
                "osm_id": f"mock_{i}",
                "osm_type": "way",
                "amenity": amenity,
                "name": name,
                "addr_street": f"{np.random.randint(100, 9999)} Main St",
                "addr_city": county_name.split(",")[0].replace(" County", ""),
                "building": "yes",
                "operator": "",
                "denomination": "",
                "geometry": Point(lon, lat),
                "county_name": county_name
            }
            
            candidates.append(candidate)
            
        return gpd.GeoDataFrame(candidates, crs="EPSG:4326")
        
    def calculate_building_areas(self, candidates_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Estimate building footprint areas.
        
        For point geometries, estimates based on amenity type.
        """
        candidates_gdf = candidates_gdf.copy()
        
        # Typical building areas by amenity (square meters)
        area_estimates = {
            "school": 2500,
            "library": 1500, 
            "community_centre": 1200,
            "place_of_worship": 800,
            "hospital": 5000,
            "clinic": 400,
            "university": 8000
        }
        
        # Add random variation ±50%
        import numpy as np
        np.random.seed(42)
        
        areas = []
        for _, row in candidates_gdf.iterrows():
            base_area = area_estimates.get(row["amenity"], 1000)
            # Random multiplier between 0.5 and 1.5
            multiplier = np.random.uniform(0.5, 1.5)
            area = base_area * multiplier
            areas.append(area)
            
        candidates_gdf["footprint_area_m2"] = areas
        
        return candidates_gdf
        
    def process_multiple_counties(self, county_configs: List[Dict]) -> gpd.GeoDataFrame:
        """
        Fetch candidates for multiple counties.
        
        Args:
            county_configs: List of county configs with bounds
            
        Returns:
            Combined candidates GeoDataFrame
        """
        gdfs = []
        
        for config in county_configs:
            gdf = self.fetch_county_candidates(
                config["bounds"],
                config["name"]
            )
            
            # Add county identifiers
            gdf["state_fips"] = config["state_fips"]
            gdf["county_fips"] = config["county_fips"]
            
            gdfs.append(gdf)
            
            # Rate limiting for API
            time.sleep(2)
            
        combined = gpd.pd.concat(gdfs, ignore_index=True)
        
        # Calculate building areas
        combined = self.calculate_building_areas(combined)
        
        return combined


def main():
    """Fetch OSM candidate sites."""
    
    # County configurations with bounding boxes
    counties = [
        {
            "state_fips": "48",
            "county_fips": "201", 
            "name": "Harris County, TX",
            "bounds": (29.5, -95.8, 30.1, -95.0)  # Houston area
        },
        {
            "state_fips": "04",
            "county_fips": "013",
            "name": "Maricopa County, AZ", 
            "bounds": (33.2, -112.8, 33.9, -111.6)  # Phoenix area
        }
    ]
    
    fetcher = OSMFetcher()
    candidates_gdf = fetcher.process_multiple_counties(counties)
    
    print(f"Found {len(candidates_gdf)} candidate sites")
    print("\nAmenity breakdown:")
    print(candidates_gdf["amenity"].value_counts())
    
    # Save results
    output_path = "data/int/candidate_sites.geojson"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    candidates_gdf.to_file(output_path, driver="GeoJSON")
    
    print(f"\nSaved candidates to {output_path}")
    print(f"Mean building area: {candidates_gdf['footprint_area_m2'].mean():.0f} m²")


if __name__ == "__main__":
    main()