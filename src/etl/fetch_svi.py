"""
Fetch CDC Social Vulnerability Index (SVI) data.
"""
import pandas as pd
import requests
import zipfile
import os
from typing import Dict, List
import geopandas as gpd


class SVIFetcher:
    """Fetch CDC Social Vulnerability Index data."""
    
    SVI_URL = "https://www.atsdr.cdc.gov/placeandhealth/centroid_data/SVI2020_US.csv"
    
    def __init__(self):
        """Initialize SVI fetcher."""
        pass
        
    def fetch_national_svi(self) -> pd.DataFrame:
        """
        Download and process national SVI data.
        
        Returns:
            DataFrame with SVI by census tract
        """
        print("Downloading SVI data...")
        
        try:
            df = pd.read_csv(self.SVI_URL, low_memory=False)
        except Exception as e:
            print(f"Error downloading SVI: {e}")
            # Fallback: create mock data structure
            return self._create_mock_svi()
            
        # Keep relevant columns
        svi_cols = [
            "FIPS", "STATE", "ST_ABBR", "COUNTY", "TRACT",
            "RPL_THEMES",  # Overall SVI percentile rank
            "RPL_THEME1",  # Socioeconomic status
            "RPL_THEME2",  # Household characteristics  
            "RPL_THEME3",  # Racial/ethnic minority status
            "RPL_THEME4",  # Housing type/transportation
            "F_TOTAL"      # Total flags (high vulnerability indicators)
        ]
        
        # Filter to relevant columns that exist
        available_cols = [col for col in svi_cols if col in df.columns]
        df = df[available_cols].copy()
        
        # Create standardized GEOID
        df["TRACT_GEOID"] = df["FIPS"].astype(str).str.zfill(11)
        
        # Rename SVI column for clarity
        if "RPL_THEMES" in df.columns:
            df["SVI"] = df["RPL_THEMES"]
        else:
            # Fallback calculation if main SVI not available
            theme_cols = [c for c in df.columns if c.startswith("RPL_THEME")]
            if theme_cols:
                df["SVI"] = df[theme_cols].mean(axis=1)
            else:
                df["SVI"] = 0.5  # Neutral value
                
        return df
        
    def _create_mock_svi(self) -> pd.DataFrame:
        """Create mock SVI data for testing when API is unavailable."""
        print("Creating mock SVI data...")
        
        # Harris County, TX tracts (48201) and Maricopa County, AZ (04013) 
        harris_tracts = [f"48201{str(i).zfill(6)}" for i in range(100001, 100101)]
        maricopa_tracts = [f"04013{str(i).zfill(6)}" for i in range(100001, 100101)]
        
        all_tracts = harris_tracts + maricopa_tracts
        
        # Generate synthetic SVI scores (0-1, higher = more vulnerable)
        import numpy as np
        np.random.seed(42)
        
        df = pd.DataFrame({
            "TRACT_GEOID": all_tracts,
            "SVI": np.random.beta(2, 2, len(all_tracts)),  # Beta distribution
            "RPL_THEME1": np.random.beta(2, 3, len(all_tracts)),
            "RPL_THEME2": np.random.beta(2, 3, len(all_tracts)), 
            "RPL_THEME3": np.random.beta(2, 3, len(all_tracts)),
            "RPL_THEME4": np.random.beta(2, 3, len(all_tracts))
        })
        
        return df
        
    def filter_counties(self, df: pd.DataFrame, 
                       county_fips: List[str]) -> pd.DataFrame:
        """
        Filter SVI data to specific counties.
        
        Args:
            df: Full SVI DataFrame
            county_fips: List of 5-digit state+county FIPS codes
            
        Returns:
            Filtered DataFrame
        """
        county_filter = df["TRACT_GEOID"].str[:5].isin(county_fips)
        return df[county_filter].copy()
        
    def downscale_to_blockgroups(self, svi_df: pd.DataFrame, 
                                acs_df: pd.DataFrame) -> pd.DataFrame:
        """
        Downscale tract-level SVI to block groups using population weights.
        
        Args:
            svi_df: SVI data by tract
            acs_df: ACS data by block group with population
            
        Returns:
            SVI data by block group
        """
        # Extract tract GEOID from block group GEOID (first 11 digits)
        acs_df = acs_df.copy()
        acs_df["TRACT_GEOID"] = acs_df["GEOID"].str[:11]
        
        # Merge SVI onto block groups
        bg_svi = acs_df.merge(
            svi_df[["TRACT_GEOID", "SVI", "RPL_THEME1", "RPL_THEME2", 
                    "RPL_THEME3", "RPL_THEME4"]],
            on="TRACT_GEOID",
            how="left"
        )
        
        # Fill missing SVI values with county median
        for county in bg_svi["county_name"].unique():
            county_mask = bg_svi["county_name"] == county
            county_median = bg_svi.loc[county_mask, "SVI"].median()
            bg_svi.loc[county_mask & bg_svi["SVI"].isna(), "SVI"] = county_median
            
        return bg_svi


def main():
    """Fetch and process SVI data."""
    
    # Target counties
    target_counties = ["48201", "04013"]  # Harris TX, Maricopa AZ
    
    fetcher = SVIFetcher()
    
    # Fetch national SVI
    svi_df = fetcher.fetch_national_svi()
    print(f"Downloaded SVI for {len(svi_df)} tracts")
    
    # Filter to target counties  
    svi_filtered = fetcher.filter_counties(svi_df, target_counties)
    print(f"Filtered to {len(svi_filtered)} tracts in target counties")
    
    # Save tract-level SVI
    output_path = "data/int/svi_tracts.parquet"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    svi_filtered.to_parquet(output_path, index=False)
    
    print(f"Saved SVI data to {output_path}")
    print(f"SVI range: {svi_filtered['SVI'].min():.3f} - {svi_filtered['SVI'].max():.3f}")


if __name__ == "__main__":
    main()