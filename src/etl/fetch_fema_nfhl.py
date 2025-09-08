"""
Fetch FEMA National Flood Hazard Layer (NFHL) data.
"""
import geopandas as gpd
import requests
import os
from typing import List, Dict
import zipfile
import io


class FEMAFetcher:
    """Fetch FEMA flood hazard data."""
    
    # FEMA Map Service Center API
    FEMA_BASE_URL = "https://hazards.fema.gov/gis/nfhl/rest/services"
    
    def __init__(self):
        """Initialize FEMA fetcher."""
        pass
        
    def fetch_county_flood_zones(self, state_fips: str, county_fips: str) -> gpd.GeoDataFrame:
        """
        Fetch flood zones for a county.
        
        In production, this would query FEMA's web services or download
        county flood zone shapefiles. For now, creates representative data.
        
        Args:
            state_fips: 2-digit state FIPS
            county_fips: 3-digit county FIPS
            
        Returns:
            GeoDataFrame with flood zone polygons
        """
        print(f"Generating flood zone data for {state_fips}{county_fips}...")
        
        # Create mock flood zone data
        return self._create_mock_flood_zones(state_fips, county_fips)
        
    def _create_mock_flood_zones(self, state_fips: str, county_fips: str) -> gpd.GeoDataFrame:
        """
        Create representative flood zone polygons.
        
        Simulates typical flood zones near water bodies and low-lying areas.
        """
        from shapely.geometry import Polygon, Point
        import numpy as np
        
        # Set coordinates based on county
        if state_fips == "48" and county_fips == "201":  # Harris County, TX
            # Houston area bounds
            bounds = (-95.8, 29.5, -95.0, 30.1)
            center_lat, center_lon = 29.8, -95.4
        elif state_fips == "04" and county_fips == "013":  # Maricopa County, AZ  
            # Phoenix area bounds
            bounds = (-112.8, 33.2, -111.6, 33.9)
            center_lat, center_lon = 33.5, -112.1
        else:
            # Generic bounds
            bounds = (-100, 40, -99, 41) 
            center_lat, center_lon = 40.5, -99.5
            
        # Generate flood zone polygons
        np.random.seed(42)
        n_zones = 15  # Number of flood zones per county
        
        geometries = []
        zone_codes = []
        
        for i in range(n_zones):
            # Create irregular polygon around water features
            center_x = np.random.uniform(bounds[0], bounds[2])
            center_y = np.random.uniform(bounds[1], bounds[3])
            
            # Generate polygon vertices
            n_vertices = np.random.randint(6, 12)
            angles = np.sort(np.random.uniform(0, 2*np.pi, n_vertices))
            
            # Vary radius to create realistic flood plain shapes  
            radii = np.random.uniform(0.01, 0.05, n_vertices)  # Degrees
            
            vertices = []
            for angle, radius in zip(angles, radii):
                x = center_x + radius * np.cos(angle)
                y = center_y + radius * np.sin(angle) 
                vertices.append((x, y))
                
            poly = Polygon(vertices)
            geometries.append(poly)
            
            # Assign flood zone codes (A/AE are 1% annual chance)
            zone_type = np.random.choice(["A", "AE", "X", "X500"], 
                                       p=[0.4, 0.3, 0.2, 0.1])
            zone_codes.append(zone_type)
            
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame({
            "FLD_ZONE": zone_codes,
            "ZONE_SUBTY": zone_codes,  # Simplified
            "FLOOD_RISK": ["High" if z in ["A", "AE"] else "Moderate" 
                          for z in zone_codes],
            "county_fips": state_fips + county_fips
        }, geometry=geometries, crs="EPSG:4326")
        
        return gdf
        
    def process_multiple_counties(self, county_configs: List[Dict]) -> gpd.GeoDataFrame:
        """
        Process flood zones for multiple counties.
        
        Args:
            county_configs: List of county configuration dicts
            
        Returns:
            Combined flood zones GeoDataFrame
        """
        gdfs = []
        
        for config in county_configs:
            print(f"Processing flood zones for {config['name']}...")
            gdf = self.fetch_county_flood_zones(
                config["state_fips"],
                config["county_fips"] 
            )
            gdf["county_name"] = config["name"]
            gdfs.append(gdf)
            
        return gpd.pd.concat(gdfs, ignore_index=True)
        
    def filter_high_risk_zones(self, flood_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Filter to high-risk flood zones (1% annual chance).
        
        Args:
            flood_gdf: All flood zones
            
        Returns:
            High-risk zones only (A, AE, VE zones)
        """
        high_risk_zones = ["A", "AE", "VE", "A99", "AO", "AH"]
        return flood_gdf[flood_gdf["FLD_ZONE"].isin(high_risk_zones)].copy()


def main():
    """Fetch and process FEMA flood data."""
    
    # County configurations  
    counties = [
        {"state_fips": "48", "county_fips": "201", "name": "Harris County, TX"},
        {"state_fips": "04", "county_fips": "013", "name": "Maricopa County, AZ"}
    ]
    
    fetcher = FEMAFetcher()
    
    # Fetch all flood zones
    flood_gdf = fetcher.process_multiple_counties(counties)
    print(f"Total flood zones: {len(flood_gdf)}")
    
    # Filter to high-risk zones for exclusion analysis
    high_risk_gdf = fetcher.filter_high_risk_zones(flood_gdf)
    print(f"High-risk flood zones: {len(high_risk_gdf)}")
    
    # Save results
    os.makedirs("data/int", exist_ok=True)
    
    flood_gdf.to_file("data/int/flood_zones_all.geojson", driver="GeoJSON")
    high_risk_gdf.to_file("data/int/flood_zones_high_risk.geojson", driver="GeoJSON")
    
    print("Saved flood zone data:")
    print(f"  All zones: data/int/flood_zones_all.geojson")  
    print(f"  High-risk: data/int/flood_zones_high_risk.geojson")
    
    print("\nFlood zone summary:")
    print(flood_gdf["FLD_ZONE"].value_counts())


if __name__ == "__main__":
    main()