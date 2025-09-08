"""
Export Land Surface Temperature (LST) from Google Earth Engine.
"""
import ee
import os
import pandas as pd
import geopandas as gpd
from typing import Dict, List, Tuple
import numpy as np


class LSTExporter:
    """Export LST composites from Google Earth Engine."""
    
    def __init__(self, service_account_path: str = None):
        """
        Initialize Earth Engine connection.
        
        Args:
            service_account_path: Path to GEE service account JSON
        """
        try:
            if service_account_path and os.path.exists(service_account_path):
                credentials = ee.ServiceAccountCredentials(
                    None, service_account_path
                )
                ee.Initialize(credentials)
            else:
                # Use API key authentication from environment variable
                api_key = os.getenv("GOOGLE_EARTH_ENGINE_API_KEY")
                if api_key:
                    ee.Initialize(api_key=api_key)
                else:
                    ee.Initialize()
            print("Google Earth Engine initialized successfully")
            self.gee_available = True
        except Exception as e:
            print(f"GEE initialization failed: {e}")
            print("Will create mock LST data instead")
            self.gee_available = False
            
    def get_county_geometry(self, state_fips: str, county_fips: str) -> ee.Geometry:
        """Get county boundary from Earth Engine."""
        counties = ee.FeatureCollection("TIGER/2018/Counties")
        county = counties.filter(ee.Filter.eq("STATEFP", state_fips)) \
                        .filter(ee.Filter.eq("COUNTYFP", county_fips))
        return county.geometry()
        
    def compute_summer_lst(self, geometry: ee.Geometry, year: int = 2023) -> ee.Image:
        """
        Compute summer LST composite from Landsat 8/9.
        
        Args:
            geometry: Area of interest
            year: Year for analysis
            
        Returns:
            LST image in Celsius
        """
        # Define summer months (June-August)
        start_date = f"{year}-06-01"
        end_date = f"{year}-09-01"
        
        # Landsat 8 & 9 collections
        l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2") \
               .filterBounds(geometry) \
               .filterDate(start_date, end_date) \
               .filter(ee.Filter.lt("CLOUD_COVER", 20))
               
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2") \
               .filterBounds(geometry) \
               .filterDate(start_date, end_date) \
               .filter(ee.Filter.lt("CLOUD_COVER", 20))
               
        # Merge collections
        landsat = l8.merge(l9)
        
        def compute_lst(image):
            """Convert thermal band to LST in Celsius."""
            # Landsat Collection 2 thermal band (ST_B10)
            lst_kelvin = image.select("ST_B10").multiply(0.00341802).add(149.0)
            lst_celsius = lst_kelvin.subtract(273.15)
            
            # Mask clouds using QA band
            qa = image.select("QA_PIXEL")
            cloud_mask = qa.bitwiseAnd(1 << 3).eq(0)  # Clear pixels
            
            return lst_celsius.updateMask(cloud_mask)
            
        # Apply LST calculation
        lst_collection = landsat.map(compute_lst)
        
        # Create median composite
        summer_lst = lst_collection.median()
        
        return summer_lst
        
    def export_county_lst(self, state_fips: str, county_fips: str, 
                         county_name: str) -> str:
        """
        Export LST raster for a county.
        
        Returns:
            Path to exported raster
        """
        if not self.gee_available:
            return self._create_mock_lst_data(state_fips, county_fips, county_name)
            
        try:
            print(f"Computing LST for {county_name}...")
            
            # Get county geometry
            county_geom = self.get_county_geometry(state_fips, county_fips)
            
            # Compute summer LST
            lst_image = self.compute_summer_lst(county_geom)
            
            # Export parameters
            export_name = f"lst_{state_fips}_{county_fips}"
            
            # Export to Google Drive (change to Cloud Storage in production)
            task = ee.batch.Export.image.toDrive(
                image=lst_image,
                description=export_name,
                folder="heatsafenet_lst",
                fileNamePrefix=export_name,
                scale=30,  # Landsat resolution
                region=county_geom,
                maxPixels=1e9
            )
            
            task.start()
            print(f"LST export task started: {export_name}")
            print("Download from Google Drive when complete")
            
            return f"drive://heatsafenet_lst/{export_name}.tif"
            
        except Exception as e:
            print(f"GEE export failed: {e}")
            return self._create_mock_lst_data(state_fips, county_fips, county_name)
            
    def _create_mock_lst_data(self, state_fips: str, county_fips: str, 
                             county_name: str) -> str:
        """Create mock LST statistics for testing."""
        
        # County-specific temperature patterns
        if state_fips == "48" and county_fips == "201":  # Harris, TX
            base_temp = 35  # Houston summer heat
            temp_range = 8
        elif state_fips == "04" and county_fips == "013":  # Maricopa, AZ
            base_temp = 40  # Phoenix extreme heat
            temp_range = 12
        else:
            base_temp = 30
            temp_range = 6
            
        # Create spatial temperature variation
        np.random.seed(int(state_fips + county_fips))
        
        # Simulate 100 sample points across county
        n_points = 100
        temps = np.random.normal(base_temp, temp_range/3, n_points)
        temps = np.clip(temps, base_temp - temp_range/2, base_temp + temp_range/2)
        
        # Create mock statistics
        lst_stats = {
            "county_fips": state_fips + county_fips,
            "county_name": county_name,
            "mean_lst_celsius": temps.mean(),
            "std_lst_celsius": temps.std(),
            "min_lst_celsius": temps.min(),
            "max_lst_celsius": temps.max(),
            "p25_lst_celsius": np.percentile(temps, 25),
            "p75_lst_celsius": np.percentile(temps, 75),
            "p95_lst_celsius": np.percentile(temps, 95)
        }
        
        # Save statistics
        output_path = f"data/int/lst_stats_{state_fips}_{county_fips}.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        import json
        with open(output_path, 'w') as f:
            json.dump(lst_stats, f, indent=2)
            
        print(f"Created mock LST statistics: {output_path}")
        print(f"Mean LST: {lst_stats['mean_lst_celsius']:.1f}°C")
        
        return output_path
        
    def process_multiple_counties(self, county_configs: List[Dict]) -> Dict:
        """Process LST for multiple counties."""
        
        results = {}
        
        for config in county_configs:
            result = self.export_county_lst(
                config["state_fips"],
                config["county_fips"], 
                config["name"]
            )
            results[config["name"]] = result
            
        return results


def main():
    """Export LST data for target counties."""
    
    # County configurations
    counties = [
        {"state_fips": "48", "county_fips": "201", "name": "Harris County, TX"},
        {"state_fips": "04", "county_fips": "013", "name": "Maricopa County, AZ"}
    ]
    
    # Initialize exporter
    exporter = LSTExporter()
    
    # Process counties
    results = exporter.process_multiple_counties(counties)
    
    print("\nLST Export Results:")
    for county, result in results.items():
        print(f"  {county}: {result}")
        
    print("\nNote: If using Google Earth Engine, download rasters from Drive")
    print("For mock data, statistics are saved to data/int/")


if __name__ == "__main__":
    main()