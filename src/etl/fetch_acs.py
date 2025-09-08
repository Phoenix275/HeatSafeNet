"""
Fetch American Community Survey (ACS) data from Census API.
"""
import pandas as pd
import requests
from typing import Dict, List
import os


class ACSFetcher:
    """Fetch ACS 5-year estimates via Census API."""
    
    BASE_URL = "https://api.census.gov/data/2022/acs/acs5"
    
    def __init__(self, api_key: str = None):
        """Initialize with optional Census API key."""
        self.api_key = api_key or os.getenv("CENSUS_API_KEY")
        
    def get_variables(self) -> Dict[str, str]:
        """Define ACS variables needed for analysis."""
        return {
            "B01003_001E": "total_population",
            "DP02_0015PE": "pct_65_plus", 
            "S1701_C02_001E": "pct_poverty",
            "B08201_002E": "no_vehicle_households",
            "B08201_001E": "total_households",
            "B28002_001E": "total_households_internet",
            "B28002_013E": "no_internet_households"
        }
        
    def fetch_county_data(self, state_fips: str, county_fips: str, 
                         geography: str = "block group") -> pd.DataFrame:
        """
        Fetch ACS data for a county at specified geography level.
        
        Args:
            state_fips: 2-digit state FIPS code
            county_fips: 3-digit county FIPS code  
            geography: Census geography level
            
        Returns:
            DataFrame with ACS variables by geography
        """
        variables = self.get_variables()
        var_list = ",".join(variables.keys())
        
        # Build API request
        params = {
            "get": var_list,
            "for": f"{geography}:*",
            "in": f"state:{state_fips} county:{county_fips}"
        }
        
        if self.api_key:
            params["key"] = self.api_key
            
        response = requests.get(self.BASE_URL, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Convert to DataFrame
        df = pd.DataFrame(data[1:], columns=data[0])
        
        # Rename columns
        df = df.rename(columns=variables)
        
        # Create GEOID
        if geography == "block group":
            df["GEOID"] = (df["state"] + df["county"] + 
                          df["tract"] + df["block group"])
        elif geography == "tract":
            df["GEOID"] = df["state"] + df["county"] + df["tract"]
            
        # Convert numeric columns
        numeric_cols = list(variables.values())
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
        # Calculate derived variables
        df["pct_no_vehicle"] = (df["no_vehicle_households"] / 
                               df["total_households"] * 100)
        df["pct_no_internet"] = (df["no_internet_households"] / 
                                df["total_households_internet"] * 100)
        
        return df
        
    def fetch_multiple_counties(self, county_configs: List[Dict]) -> pd.DataFrame:
        """
        Fetch data for multiple counties and combine.
        
        Args:
            county_configs: List of dicts with 'state_fips', 'county_fips', 'name'
            
        Returns:
            Combined DataFrame
        """
        dfs = []
        
        for config in county_configs:
            print(f"Fetching ACS data for {config['name']}...")
            df = self.fetch_county_data(
                config["state_fips"], 
                config["county_fips"]
            )
            df["county_name"] = config["name"]
            dfs.append(df)
            
        return pd.concat(dfs, ignore_index=True)


def main():
    """Example usage - fetch data for Harris and Maricopa counties."""
    
    # County configurations
    counties = [
        {"state_fips": "48", "county_fips": "201", "name": "Harris County, TX"},
        {"state_fips": "04", "county_fips": "013", "name": "Maricopa County, AZ"}
    ]
    
    fetcher = ACSFetcher()
    df = fetcher.fetch_multiple_counties(counties)
    
    # Save to file
    output_path = "data/int/acs_blockgroups.parquet"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_parquet(output_path, index=False)
    
    print(f"Saved {len(df)} block groups to {output_path}")
    print(f"Columns: {list(df.columns)}")


if __name__ == "__main__":
    main()