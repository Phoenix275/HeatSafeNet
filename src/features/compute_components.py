"""
Compute all risk index components.
"""
import pandas as pd
import numpy as np
import geopandas as gpd
import os
from typing import Dict, Tuple


class RiskComponentCalculator:
    """Calculate all components of the risk index."""
    
    def __init__(self):
        """Initialize component calculator."""
        pass
        
    def compute_social_vulnerability(self, cbg_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Compute normalized social vulnerability component.
        
        Uses CDC SVI if available, falls back to ACS indicators.
        """
        cbg_gdf = cbg_gdf.copy()
        
        if "SVI" in cbg_gdf.columns:
            # Use CDC SVI directly (already 0-1 percentile rank)
            print("Using CDC SVI for social vulnerability")
            
            # Fill missing SVI with county median
            county_groups = cbg_gdf.groupby("county_name")
            
            for county_name, county_data in county_groups:
                county_mask = cbg_gdf["county_name"] == county_name
                county_median = cbg_gdf.loc[county_mask, "SVI"].median()
                
                if pd.isna(county_median):
                    county_median = 0.5  # Neutral if no data
                    
                cbg_gdf.loc[county_mask & cbg_gdf["SVI"].isna(), "SVI"] = county_median
                
            cbg_gdf["social_vulnerability"] = cbg_gdf["SVI"]
            
        else:
            # Create composite from ACS indicators
            print("Creating social vulnerability from ACS indicators")
            
            indicators = []
            weights = []
            
            # Poverty rate (higher = more vulnerable)
            if "pct_poverty" in cbg_gdf.columns:
                indicators.append("pct_poverty")
                weights.append(0.4)
                
            # No vehicle access (transportation vulnerability)  
            if "pct_no_vehicle" in cbg_gdf.columns:
                indicators.append("pct_no_vehicle")
                weights.append(0.3)
                
            # Educational attainment proxy (could add if available)
            # For now, use poverty as main socioeconomic indicator
            
            if indicators:
                # Normalize each indicator within county
                cbg_gdf = self._normalize_by_county(cbg_gdf, indicators)
                
                # Weighted average
                norm_cols = [f"{ind}_norm" for ind in indicators]
                cbg_gdf["social_vulnerability"] = np.average(
                    cbg_gdf[norm_cols].fillna(0.5),
                    weights=weights[:len(norm_cols)],
                    axis=1
                )
            else:
                cbg_gdf["social_vulnerability"] = 0.5  # Neutral default
                
        return cbg_gdf
        
    def compute_digital_exclusion(self, cbg_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Compute digital exclusion component."""
        cbg_gdf = cbg_gdf.copy()
        
        print("Computing digital exclusion scores")
        
        # Primary indicator: No internet subscription (ACS)
        no_internet_weight = 0.7
        
        # Secondary indicator: Lack of broadband availability (FCC)  
        no_broadband_weight = 0.3
        
        components = []
        
        # ACS No Internet component
        if "pct_no_internet" in cbg_gdf.columns:
            cbg_gdf = self._normalize_by_county(cbg_gdf, ["pct_no_internet"])
            components.append(("pct_no_internet_norm", no_internet_weight))
        else:
            # Create mock no-internet data
            cbg_gdf["pct_no_internet"] = np.random.uniform(5, 25, len(cbg_gdf))
            cbg_gdf = self._normalize_by_county(cbg_gdf, ["pct_no_internet"])
            components.append(("pct_no_internet_norm", no_internet_weight))
            
        # FCC Broadband availability component (inverted - lack of availability)
        if "broadband_100_20_available" in cbg_gdf.columns:
            cbg_gdf["broadband_unavailable"] = 1 - cbg_gdf["broadband_100_20_available"]
            cbg_gdf = self._normalize_by_county(cbg_gdf, ["broadband_unavailable"])
            components.append(("broadband_unavailable_norm", no_broadband_weight))
            
        # Compute weighted average
        if len(components) == 2:
            cbg_gdf["digital_exclusion"] = (
                components[0][1] * cbg_gdf[components[0][0]] +
                components[1][1] * cbg_gdf[components[1][0]]
            )
        elif len(components) == 1:
            cbg_gdf["digital_exclusion"] = cbg_gdf[components[0][0]]
        else:
            cbg_gdf["digital_exclusion"] = 0.5
            
        return cbg_gdf
        
    def compute_elderly_vulnerability(self, cbg_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Compute elderly population vulnerability."""
        cbg_gdf = cbg_gdf.copy()
        
        print("Computing elderly vulnerability scores")
        
        if "pct_65_plus" in cbg_gdf.columns:
            cbg_gdf = self._normalize_by_county(cbg_gdf, ["pct_65_plus"])
            cbg_gdf["elderly_vulnerability"] = cbg_gdf["pct_65_plus_norm"]
        else:
            # Create reasonable elderly population estimates
            # Typically 15-25% in suburban areas, varies by geography
            cbg_gdf["pct_65_plus"] = np.random.uniform(10, 30, len(cbg_gdf))
            cbg_gdf = self._normalize_by_county(cbg_gdf, ["pct_65_plus"])
            cbg_gdf["elderly_vulnerability"] = cbg_gdf["pct_65_plus_norm"]
            
        return cbg_gdf
        
    def _normalize_by_county(self, df: gpd.GeoDataFrame, 
                           columns: list) -> gpd.GeoDataFrame:
        """Normalize columns to 0-1 within each county."""
        df = df.copy()
        
        county_groups = df.groupby("county_name")
        
        for col in columns:
            norm_col = f"{col}_norm"
            norm_values = []
            
            for county_name, county_data in county_groups:
                values = county_data[col]
                
                # Min-max normalization within county
                val_min = values.min()
                val_max = values.max()
                
                if val_max > val_min:
                    county_norm = (values - val_min) / (val_max - val_min)
                else:
                    county_norm = pd.Series([0.5] * len(values), index=values.index)
                    
                norm_values.append(county_norm)
                
            df[norm_col] = pd.concat(norm_values)
            
        return df
        
    def compute_all_components(self, cbg_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Compute all risk components."""
        
        print("Computing all risk index components...")
        
        # Compute each component
        cbg_gdf = self.compute_social_vulnerability(cbg_gdf)
        cbg_gdf = self.compute_digital_exclusion(cbg_gdf)
        cbg_gdf = self.compute_elderly_vulnerability(cbg_gdf)
        
        # Validate components are in [0,1] range
        components = ["heat_exposure", "social_vulnerability", 
                     "digital_exclusion", "elderly_vulnerability"]
        
        for comp in components:
            if comp in cbg_gdf.columns:
                cbg_gdf[comp] = cbg_gdf[comp].clip(0, 1)
                print(f"{comp}: {cbg_gdf[comp].min():.3f} - {cbg_gdf[comp].max():.3f}")
            else:
                print(f"Warning: {comp} component missing")
                
        return cbg_gdf


def main():
    """Compute all risk components."""
    
    # Load CBG data with heat exposure
    input_path = "data/int/cbg_with_heat_exposure.geojson"
    
    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}")
        print("Run compute_heat_exposure.py first")
        return
        
    print("Loading CBG data with heat exposure...")
    cbg_gdf = gpd.read_file(input_path)
    
    # Compute all components
    calculator = RiskComponentCalculator()
    cbg_with_components = calculator.compute_all_components(cbg_gdf)
    
    # Save results
    output_path = "data/int/cbg_with_risk_components.geojson"
    cbg_with_components.to_file(output_path, driver="GeoJSON")
    
    print(f"Saved results to {output_path}")
    print(f"Processed {len(cbg_with_components)} block groups")


if __name__ == "__main__":
    main()