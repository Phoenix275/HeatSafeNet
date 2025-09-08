"""
Compute heat exposure component of risk index.
"""
import pandas as pd
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_bounds
import os
from typing import Dict, Tuple
import json


class HeatExposureCalculator:
    """Calculate heat exposure for census block groups."""
    
    def __init__(self):
        """Initialize heat exposure calculator."""
        pass
        
    def load_lst_statistics(self, county_fips: str) -> Dict:
        """Load LST statistics from GEE export or mock data."""
        
        # Look for LST statistics files
        state_fips = county_fips[:2]
        county_code = county_fips[2:]
        
        stats_path = f"data/int/lst_stats_{state_fips}_{county_code}.json"
        
        if os.path.exists(stats_path):
            with open(stats_path, 'r') as f:
                return json.load(f)
        else:
            # Create default statistics
            return self._create_default_lst_stats(county_fips)
            
    def _create_default_lst_stats(self, county_fips: str) -> Dict:
        """Create default LST statistics if no data available."""
        
        # County-specific defaults based on climate
        if county_fips == "48201":  # Harris County, TX  
            base_temp = 35
            temp_range = 8
        elif county_fips == "04013":  # Maricopa County, AZ
            base_temp = 40
            temp_range = 12
        else:
            base_temp = 30
            temp_range = 6
            
        return {
            "county_fips": county_fips,
            "mean_lst_celsius": base_temp,
            "std_lst_celsius": temp_range / 3,
            "min_lst_celsius": base_temp - temp_range / 2,
            "max_lst_celsius": base_temp + temp_range / 2,
            "p25_lst_celsius": base_temp - temp_range / 4,
            "p75_lst_celsius": base_temp + temp_range / 4,
            "p95_lst_celsius": base_temp + temp_range / 2
        }
        
    def simulate_cbg_temperatures(self, cbg_gdf: gpd.GeoDataFrame, 
                                 lst_stats: Dict) -> gpd.GeoDataFrame:
        """
        Simulate block group temperatures based on spatial patterns.
        
        In production, would use zonal statistics from LST raster.
        """
        cbg_gdf = cbg_gdf.copy()
        
        # Set random seed for reproducibility
        county_seed = int(lst_stats["county_fips"]) % 10000
        np.random.seed(county_seed)
        
        n_bg = len(cbg_gdf)
        
        # Simulate spatial temperature variation
        # Assume urban heat island effects and geographic patterns
        
        # Get county bounds for spatial modeling
        bounds = cbg_gdf.total_bounds  # minx, miny, maxx, maxy
        
        # Calculate centroid coordinates
        cbg_gdf["centroid_lon"] = cbg_gdf.geometry.centroid.x
        cbg_gdf["centroid_lat"] = cbg_gdf.geometry.centroid.y
        
        # Normalize coordinates to [0,1]
        lon_norm = (cbg_gdf["centroid_lon"] - bounds[0]) / (bounds[2] - bounds[0])
        lat_norm = (cbg_gdf["centroid_lat"] - bounds[1]) / (bounds[3] - bounds[1])
        
        # Create temperature gradients
        # Urban core (center) tends to be hotter
        center_dist = np.sqrt((lon_norm - 0.5)**2 + (lat_norm - 0.5)**2)
        urban_effect = 3 * (1 - center_dist)  # Up to 3°C urban heat island
        
        # Add random variation
        random_variation = np.random.normal(0, lst_stats["std_lst_celsius"], n_bg)
        
        # Combine effects
        base_temp = lst_stats["mean_lst_celsius"]
        cbg_temperatures = base_temp + urban_effect + random_variation
        
        # Clip to reasonable bounds
        temp_min = lst_stats["min_lst_celsius"]
        temp_max = lst_stats["max_lst_celsius"]
        cbg_temperatures = np.clip(cbg_temperatures, temp_min, temp_max)
        
        cbg_gdf["summer_lst_celsius"] = cbg_temperatures
        
        return cbg_gdf
        
    def compute_heat_exposure_score(self, cbg_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Compute normalized heat exposure scores (0-1, higher = more exposed).
        
        Args:
            cbg_gdf: CBGs with temperature data
            
        Returns:
            CBGs with heat exposure scores
        """
        cbg_gdf = cbg_gdf.copy()
        
        # Group by county for normalization
        county_groups = cbg_gdf.groupby("county_name")
        
        heat_scores = []
        
        for county_name, county_data in county_groups:
            temps = county_data["summer_lst_celsius"]
            
            # Normalize to 0-1 within county (min-max scaling)
            temp_min = temps.min()
            temp_max = temps.max()
            
            if temp_max > temp_min:
                county_scores = (temps - temp_min) / (temp_max - temp_min)
            else:
                county_scores = pd.Series([0.5] * len(temps), index=temps.index)
                
            heat_scores.append(county_scores)
            
        # Combine all scores
        cbg_gdf["heat_exposure"] = pd.concat(heat_scores)
        
        return cbg_gdf
        
    def process_multiple_counties(self, cbg_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Process heat exposure for all counties in dataset."""
        
        print("Computing heat exposure scores...")
        
        # Process each county
        county_groups = cbg_gdf.groupby("county_name")
        processed_counties = []
        
        for county_name, county_data in county_groups:
            print(f"Processing {county_name}...")
            
            # Get county FIPS
            county_fips = county_data.iloc[0]["GEOID"][:5]
            
            # Load LST statistics
            lst_stats = self.load_lst_statistics(county_fips)
            
            # Simulate temperatures
            county_with_temps = self.simulate_cbg_temperatures(county_data, lst_stats)
            
            # Compute exposure scores
            county_with_scores = self.compute_heat_exposure_score(county_with_temps)
            
            processed_counties.append(county_with_scores)
            
        # Combine results
        result = gpd.pd.concat(processed_counties, ignore_index=True)
        
        print(f"Heat exposure computed for {len(result)} block groups")
        print(f"Temperature range: {result['summer_lst_celsius'].min():.1f}°C - {result['summer_lst_celsius'].max():.1f}°C")
        print(f"Heat exposure range: {result['heat_exposure'].min():.3f} - {result['heat_exposure'].max():.3f}")
        
        return result


def main():
    """Compute heat exposure for all CBGs."""
    
    # Load CBG data
    cbg_path = "data/int/cbg_with_demographics.geojson"
    
    if not os.path.exists(cbg_path):
        print(f"CBG file not found: {cbg_path}")
        print("Run build_cbgs.py first")
        return
        
    print("Loading CBG data...")
    cbg_gdf = gpd.read_file(cbg_path)
    
    # Compute heat exposure
    calculator = HeatExposureCalculator()
    cbg_with_heat = calculator.process_multiple_counties(cbg_gdf)
    
    # Save results
    output_path = "data/int/cbg_with_heat_exposure.geojson" 
    cbg_with_heat.to_file(output_path, driver="GeoJSON")
    
    print(f"Saved results to {output_path}")


if __name__ == "__main__":
    main()