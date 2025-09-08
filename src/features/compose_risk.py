"""
Compose final risk index from components.
"""
import pandas as pd
import numpy as np
import geopandas as gpd
import os
from typing import Dict


class RiskIndexComposer:
    """Compose final risk index from components."""
    
    DEFAULT_WEIGHTS = {
        "heat_exposure": 0.35,
        "social_vulnerability": 0.30,
        "digital_exclusion": 0.25,
        "elderly_vulnerability": 0.10
    }
    
    def __init__(self, weights: Dict[str, float] = None):
        """
        Initialize composer with component weights.
        
        Args:
            weights: Component weights (must sum to 1.0)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS
        
        # Validate weights
        weight_sum = sum(self.weights.values())
        if not np.isclose(weight_sum, 1.0, rtol=1e-5):
            raise ValueError(f"Weights must sum to 1.0, got {weight_sum}")
            
    def compose_risk_index(self, cbg_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Compose final risk index from components.
        
        Args:
            cbg_gdf: CBGs with risk components
            
        Returns:
            CBGs with final risk index
        """
        cbg_gdf = cbg_gdf.copy()
        
        print("Composing final risk index...")
        print(f"Component weights: {self.weights}")
        
        # Check which components are available
        available_components = []
        missing_components = []
        
        for component in self.weights.keys():
            if component in cbg_gdf.columns:
                available_components.append(component)
            else:
                missing_components.append(component)
                
        if missing_components:
            print(f"Warning: Missing components: {missing_components}")
            
        # Renormalize weights for available components
        available_weight_sum = sum(self.weights[c] for c in available_components)
        normalized_weights = {
            c: self.weights[c] / available_weight_sum 
            for c in available_components
        }
        
        print(f"Using components: {list(normalized_weights.keys())}")
        print(f"Normalized weights: {normalized_weights}")
        
        # Compute weighted average
        risk_values = np.zeros(len(cbg_gdf))
        
        for component, weight in normalized_weights.items():
            component_values = cbg_gdf[component].fillna(0.5)  # Neutral for missing
            risk_values += weight * component_values
            
        # Ensure risk is in [0, 1] range  
        cbg_gdf["risk"] = np.clip(risk_values, 0, 1)
        
        return cbg_gdf
        
    def compute_demand_weights(self, cbg_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Compute population-weighted demand for optimization.
        
        Args:
            cbg_gdf: CBGs with risk and population
            
        Returns:
            CBGs with demand weights
        """
        cbg_gdf = cbg_gdf.copy()
        
        print("Computing demand weights for optimization...")
        
        # Use total population if available
        pop_column = None
        for col in ["total_population", "B01003_001E", "population"]:
            if col in cbg_gdf.columns:
                pop_column = col
                break
                
        if pop_column is None:
            print("Warning: No population data found, using uniform population")
            cbg_gdf["population"] = 1000  # Uniform population
            pop_column = "population"
            
        # Compute risk-weighted population
        cbg_gdf["demand_weight"] = cbg_gdf["risk"] * cbg_gdf[pop_column]
        
        # Also compute square-root version for sensitivity analysis
        cbg_gdf["demand_weight_sqrt"] = cbg_gdf["risk"] * np.sqrt(cbg_gdf[pop_column])
        
        print(f"Demand weight range: {cbg_gdf['demand_weight'].min():.1f} - {cbg_gdf['demand_weight'].max():.1f}")
        print(f"Total weighted demand: {cbg_gdf['demand_weight'].sum():.0f}")
        
        return cbg_gdf
        
    def compute_risk_quartiles(self, cbg_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Compute risk quartiles for equity analysis."""
        cbg_gdf = cbg_gdf.copy()
        
        # Compute quartiles by county
        county_groups = cbg_gdf.groupby("county_name")
        
        risk_quartiles = []
        
        for county_name, county_data in county_groups:
            county_risk = county_data["risk"]
            quartile_thresholds = county_risk.quantile([0.25, 0.5, 0.75])
            
            county_quartiles = pd.cut(
                county_risk,
                bins=[-np.inf] + list(quartile_thresholds) + [np.inf],
                labels=["Q1_Low", "Q2_Med_Low", "Q3_Med_High", "Q4_High"],
                include_lowest=True
            )
            
            risk_quartiles.append(county_quartiles)
            
        cbg_gdf["risk_quartile"] = pd.concat(risk_quartiles)
        
        return cbg_gdf
        
    def generate_summary_statistics(self, cbg_gdf: gpd.GeoDataFrame) -> Dict:
        """Generate summary statistics for the risk index."""
        
        stats = {}
        
        # Overall statistics
        stats["n_block_groups"] = len(cbg_gdf)
        stats["risk_mean"] = cbg_gdf["risk"].mean()
        stats["risk_std"] = cbg_gdf["risk"].std()
        stats["risk_min"] = cbg_gdf["risk"].min()
        stats["risk_max"] = cbg_gdf["risk"].max()
        
        # Component contributions
        stats["components"] = {}
        for component in self.weights.keys():
            if component in cbg_gdf.columns:
                stats["components"][component] = {
                    "mean": cbg_gdf[component].mean(),
                    "std": cbg_gdf[component].std(),
                    "weight": self.weights[component]
                }
                
        # County-level statistics  
        stats["by_county"] = {}
        county_groups = cbg_gdf.groupby("county_name")
        
        for county_name, county_data in county_groups:
            pop_col = "total_population" if "total_population" in county_data.columns else "population"
            
            stats["by_county"][county_name] = {
                "n_block_groups": len(county_data),
                "risk_mean": county_data["risk"].mean(),
                "population_total": county_data[pop_col].sum() if pop_col in county_data.columns else None,
                "high_risk_share": (county_data["risk"] > 0.75).mean(),
                "total_weighted_demand": county_data["demand_weight"].sum()
            }
            
        return stats
        
    def process_full_pipeline(self, cbg_gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, Dict]:
        """Process full risk composition pipeline."""
        
        # Compose risk index
        cbg_with_risk = self.compose_risk_index(cbg_gdf)
        
        # Compute demand weights
        cbg_with_demand = self.compute_demand_weights(cbg_with_risk)
        
        # Compute risk quartiles
        cbg_final = self.compute_risk_quartiles(cbg_with_demand)
        
        # Generate statistics
        stats = self.generate_summary_statistics(cbg_final)
        
        return cbg_final, stats


def main():
    """Compose final risk index."""
    
    # Load CBG data with components
    input_path = "data/int/cbg_with_risk_components.geojson"
    
    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}")
        print("Run compute_components.py first")
        return
        
    print("Loading CBG data with risk components...")
    cbg_gdf = gpd.read_file(input_path)
    
    # Compose risk index
    composer = RiskIndexComposer()
    cbg_final, stats = composer.process_full_pipeline(cbg_gdf)
    
    # Save results
    output_path = "data/out/cbg_with_risk_index.geojson"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    cbg_final.to_file(output_path, driver="GeoJSON")
    
    # Save statistics
    import json
    stats_path = "data/out/risk_index_stats.json"
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2, default=str)
        
    print(f"Saved final risk index to {output_path}")
    print(f"Saved statistics to {stats_path}")
    
    print("\n=== Risk Index Summary ===")
    print(f"Block groups processed: {stats['n_block_groups']}")
    print(f"Risk index range: {stats['risk_min']:.3f} - {stats['risk_max']:.3f}")
    print(f"Risk index mean: {stats['risk_mean']:.3f} (std: {stats['risk_std']:.3f})")
    
    print("\nBy county:")
    for county, county_stats in stats["by_county"].items():
        print(f"  {county}: {county_stats['n_block_groups']} BGs, "
              f"mean risk {county_stats['risk_mean']:.3f}, "
              f"{county_stats['high_risk_share']:.1%} high risk")


if __name__ == "__main__":
    main()