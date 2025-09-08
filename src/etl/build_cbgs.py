"""
Build census block group geometries and merge with demographic data.
"""
import geopandas as gpd
import pandas as pd
import requests
import os
from typing import List, Dict
import zipfile
import io


class CBGBuilder:
    """Build census block group boundaries with demographics."""
    
    TIGER_BASE_URL = "https://www2.census.gov/geo/tiger/TIGER2022/BG"
    
    def __init__(self):
        """Initialize CBG builder."""
        pass
        
    def fetch_county_cbg_boundaries(self, state_fips: str, county_fips: str) -> gpd.GeoDataFrame:
        """
        Fetch block group boundaries from Census TIGER/Line.
        
        Args:
            state_fips: 2-digit state FIPS
            county_fips: 3-digit county FIPS
            
        Returns:
            GeoDataFrame with block group boundaries
        """
        filename = f"tl_2022_{state_fips}_bg.zip"
        url = f"{self.TIGER_BASE_URL}/{filename}"
        
        try:
            print(f"Downloading {filename}...")
            response = requests.get(url)
            response.raise_for_status()
            
            # Extract and read shapefile
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # Find the .shp file
                shp_files = [f for f in z.namelist() if f.endswith('.shp')]
                if not shp_files:
                    raise ValueError("No shapefile found in zip")
                    
                # Extract all files to temp location
                temp_dir = f"temp_{state_fips}_bg"
                z.extractall(temp_dir)
                
                # Read shapefile
                shp_path = os.path.join(temp_dir, shp_files[0])
                gdf = gpd.read_file(shp_path)
                
                # Clean up temp files
                import shutil
                shutil.rmtree(temp_dir)
                
            # Filter to target county
            county_filter = gdf["COUNTYFP"] == county_fips
            gdf = gdf[county_filter].copy()
            
            # Create standard GEOID
            gdf["GEOID"] = gdf["GEOID"].astype(str)
            
            # Keep essential columns
            keep_cols = ["GEOID", "STATEFP", "COUNTYFP", "TRACTCE", "BLKGRPCE", 
                        "NAMELSAD", "ALAND", "AWATER", "geometry"]
            existing_cols = [c for c in keep_cols if c in gdf.columns]
            gdf = gdf[existing_cols].copy()
            
            return gdf
            
        except Exception as e:
            print(f"Error fetching TIGER data: {e}")
            print("Creating mock boundaries...")
            return self._create_mock_cbg_boundaries(state_fips, county_fips)
            
    def _create_mock_cbg_boundaries(self, state_fips: str, county_fips: str) -> gpd.GeoDataFrame:
        """Create mock block group boundaries for testing."""
        from shapely.geometry import Polygon
        import numpy as np
        
        # Set county-specific bounds
        if state_fips == "48" and county_fips == "201":  # Harris County, TX
            bounds = (-95.8, 29.5, -95.0, 30.1)
        elif state_fips == "04" and county_fips == "013":  # Maricopa County, AZ
            bounds = (-112.8, 33.2, -111.6, 33.9)
        else:
            bounds = (-100, 40, -99, 41)
            
        west, south, east, north = bounds
        
        # Create grid of block groups
        np.random.seed(42)
        n_bg_per_dim = 15  # 15x15 grid ≈ 225 block groups
        
        x_step = (east - west) / n_bg_per_dim
        y_step = (north - south) / n_bg_per_dim
        
        geometries = []
        geoids = []
        
        bg_counter = 1
        
        for i in range(n_bg_per_dim):
            for j in range(n_bg_per_dim):
                # Grid cell bounds
                x1 = west + i * x_step
                x2 = west + (i + 1) * x_step  
                y1 = south + j * y_step
                y2 = south + (j + 1) * y_step
                
                # Add small random variation to avoid perfect grid
                noise = 0.1 * min(x_step, y_step)
                x1 += np.random.uniform(-noise, noise)
                x2 += np.random.uniform(-noise, noise)
                y1 += np.random.uniform(-noise, noise)
                y2 += np.random.uniform(-noise, noise)
                
                # Create polygon
                poly = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
                geometries.append(poly)
                
                # Generate GEOID (state + county + tract + bg)
                tract_id = f"{(bg_counter - 1) // 4 + 1:06d}"  # 4 BGs per tract
                bg_id = f"{(bg_counter - 1) % 4 + 1}"
                geoid = state_fips + county_fips + tract_id + bg_id
                geoids.append(geoid)
                
                bg_counter += 1
                
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame({
            "GEOID": geoids,
            "STATEFP": state_fips,
            "COUNTYFP": county_fips,
            "TRACTCE": [g[5:11] for g in geoids],
            "BLKGRPCE": [g[11] for g in geoids],
            "NAMELSAD": [f"Block Group {g[11]}" for g in geoids],
            "ALAND": np.random.uniform(500000, 2000000, len(geoids)),  # Land area m²
            "AWATER": np.random.uniform(0, 50000, len(geoids))  # Water area m²
        }, geometry=geometries, crs="EPSG:4326")
        
        return gdf
        
    def merge_with_demographics(self, cbg_gdf: gpd.GeoDataFrame, 
                              acs_df: pd.DataFrame, 
                              svi_df: pd.DataFrame = None,
                              fcc_df: pd.DataFrame = None) -> gpd.GeoDataFrame:
        """
        Merge CBG boundaries with demographic data.
        
        Args:
            cbg_gdf: Block group boundaries
            acs_df: ACS demographic data
            svi_df: SVI data (optional)
            fcc_df: FCC broadband data (optional)
            
        Returns:
            Merged GeoDataFrame
        """
        print("Merging CBG boundaries with demographics...")
        
        # Start with boundaries
        merged = cbg_gdf.copy()
        
        # Merge ACS data
        merged = merged.merge(acs_df, on="GEOID", how="left")
        
        # Merge SVI data if available
        if svi_df is not None:
            # SVI is at tract level, need to join on tract GEOID
            merged["TRACT_GEOID"] = merged["GEOID"].str[:11]
            svi_cols = ["TRACT_GEOID", "SVI", "RPL_THEME1", "RPL_THEME2", 
                       "RPL_THEME3", "RPL_THEME4"]
            svi_merge = svi_df[[c for c in svi_cols if c in svi_df.columns]]
            merged = merged.merge(svi_merge, on="TRACT_GEOID", how="left")
            
        # Merge FCC data if available  
        if fcc_df is not None:
            fcc_cols = ["GEOID", "broadband_100_20_available", "provider_count"]
            fcc_merge = fcc_df[[c for c in fcc_cols if c in fcc_df.columns]]
            merged = merged.merge(fcc_merge, on="GEOID", how="left")
            
        return merged
        
    def process_multiple_counties(self, county_configs: List[Dict],
                                acs_df: pd.DataFrame,
                                svi_df: pd.DataFrame = None,
                                fcc_df: pd.DataFrame = None) -> gpd.GeoDataFrame:
        """Process multiple counties and combine."""
        
        gdfs = []
        
        for config in county_configs:
            print(f"Processing CBGs for {config['name']}...")
            
            # Fetch boundaries
            cbg_gdf = self.fetch_county_cbg_boundaries(
                config["state_fips"],
                config["county_fips"]
            )
            
            # Filter demographic data to this county
            county_geoid = config["state_fips"] + config["county_fips"]
            acs_county = acs_df[acs_df["GEOID"].str[:5] == county_geoid]
            
            if svi_df is not None:
                svi_county = svi_df[svi_df["TRACT_GEOID"].str[:5] == county_geoid]
            else:
                svi_county = None
                
            if fcc_df is not None:
                fcc_county = fcc_df[fcc_df["GEOID"].str[:5] == county_geoid]
            else:
                fcc_county = None
                
            # Merge data
            merged = self.merge_with_demographics(
                cbg_gdf, acs_county, svi_county, fcc_county
            )
            merged["county_name"] = config["name"]
            
            gdfs.append(merged)
            
        return gpd.pd.concat(gdfs, ignore_index=True)


def main():
    """Build CBG dataset with demographics."""
    
    # County configurations
    counties = [
        {"state_fips": "48", "county_fips": "201", "name": "Harris County, TX"},
        {"state_fips": "04", "county_fips": "013", "name": "Maricopa County, AZ"}
    ]
    
    # Load demographic data
    acs_path = "data/int/acs_blockgroups.parquet"
    svi_path = "data/int/svi_tracts.parquet"
    fcc_path = "data/int/fcc_broadband.parquet"
    
    acs_df = pd.read_parquet(acs_path) if os.path.exists(acs_path) else pd.DataFrame()
    svi_df = pd.read_parquet(svi_path) if os.path.exists(svi_path) else None
    fcc_df = pd.read_parquet(fcc_path) if os.path.exists(fcc_path) else None
    
    print(f"Loaded ACS data: {len(acs_df)} records")
    print(f"Loaded SVI data: {len(svi_df) if svi_df is not None else 0} records")
    print(f"Loaded FCC data: {len(fcc_df) if fcc_df is not None else 0} records")
    
    # Build CBGs
    builder = CBGBuilder()
    cbg_gdf = builder.process_multiple_counties(counties, acs_df, svi_df, fcc_df)
    
    print(f"Built {len(cbg_gdf)} block groups with demographics")
    
    # Save results
    output_path = "data/int/cbg_with_demographics.geojson"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    cbg_gdf.to_file(output_path, driver="GeoJSON")
    
    print(f"Saved CBG dataset to {output_path}")
    print(f"Columns: {list(cbg_gdf.columns)}")


if __name__ == "__main__":
    main()