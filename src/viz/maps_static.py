"""
Generate static maps for paper and reports.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import geopandas as gpd
import pandas as pd
import numpy as np
import contextily as ctx
from matplotlib import cm
from matplotlib.colors import Normalize
import json
import os
from typing import Dict, List, Tuple


class StaticMapGenerator:
    """Generate static maps for publication."""
    
    def __init__(self, style: str = "paper"):
        """
        Initialize map generator.
        
        Args:
            style: "paper" for publication, "report" for policy briefs
        """
        self.style = style
        self._setup_style()
        
    def _setup_style(self):
        """Configure matplotlib style."""
        if self.style == "paper":
            plt.style.use('default')
            plt.rcParams.update({
                'font.size': 10,
                'font.family': 'Arial',
                'axes.linewidth': 0.5,
                'xtick.major.width': 0.5,
                'ytick.major.width': 0.5
            })
        else:  # report style
            plt.rcParams.update({
                'font.size': 12,
                'font.family': 'Arial',
                'axes.linewidth': 1.0
            })
            
    def load_data(self) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """Load spatial data for mapping."""
        
        # Load CBGs with risk index
        cbg_path = "data/out/cbg_with_risk_index.geojson"
        if os.path.exists(cbg_path):
            cbg_gdf = gpd.read_file(cbg_path)
        else:
            raise FileNotFoundError(f"CBG data not found: {cbg_path}")
            
        # Load candidate sites
        candidates_path = "data/int/candidate_sites.geojson"
        if os.path.exists(candidates_path):
            candidates_gdf = gpd.read_file(candidates_path)
        else:
            raise FileNotFoundError(f"Candidates data not found: {candidates_path}")
            
        return cbg_gdf, candidates_gdf
        
    def create_risk_map(self, 
                       cbg_gdf: gpd.GeoDataFrame, 
                       county_name: str,
                       title: str = None) -> plt.Figure:
        """Create risk index choropleth map."""
        
        # Filter to county
        county_data = cbg_gdf[cbg_gdf["county_name"] == county_name].copy()
        
        if len(county_data) == 0:
            raise ValueError(f"No data found for county: {county_name}")
            
        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(12, 10))
        
        # Convert to Web Mercator for contextily
        county_data = county_data.to_crs('EPSG:3857')
        
        # Plot risk choropleth
        county_data.plot(
            column='risk',
            cmap='YlOrRd',
            linewidth=0.3,
            edgecolor='white',
            alpha=0.8,
            ax=ax,
            legend=True,
            legend_kwds={
                'label': 'Heat × Digital Exclusion Risk',
                'shrink': 0.8,
                'aspect': 30
            }
        )
        
        # Add basemap
        try:
            ctx.add_basemap(ax, crs=county_data.crs, source=ctx.providers.CartoDB.Positron, alpha=0.5)
        except Exception as e:
            print(f"Could not add basemap: {e}")
            
        # Style map
        ax.set_axis_off()
        
        if title is None:
            title = f"Heat × Digital Exclusion Risk\n{county_name}"
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # Add top 10 risk areas labels
        top_risk = county_data.nlargest(10, 'risk')
        
        for idx, row in top_risk.iterrows():
            centroid = row.geometry.centroid
            ax.annotate(
                f"{row['risk']:.2f}",
                xy=(centroid.x, centroid.y),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=8,
                bbox=dict(boxstyle='round,pad=0.2', facecolor='yellow', alpha=0.7),
                ha='left'
            )
            
        plt.tight_layout()
        return fig
        
    def create_solution_map(self,
                          cbg_gdf: gpd.GeoDataFrame,
                          candidates_gdf: gpd.GeoDataFrame,
                          solution_data: Dict,
                          county_name: str,
                          scenario: str = "walk",
                          K: int = 10) -> plt.Figure:
        """Create map showing optimization solution."""
        
        # Filter to county
        county_cbg = cbg_gdf[cbg_gdf["county_name"] == county_name].copy()
        county_candidates = candidates_gdf[candidates_gdf["county_name"] == county_name].copy()
        
        # Get solution results
        if county_name not in solution_data:
            raise ValueError(f"No solution data for {county_name}")
            
        county_solution = solution_data[county_name]
        
        if scenario not in county_solution:
            raise ValueError(f"No solution for scenario {scenario}")
            
        scenario_solution = county_solution[scenario]
        
        if f"K_{K}" not in scenario_solution:
            raise ValueError(f"No solution for K={K}")
            
        solution = scenario_solution[f"K_{K}"]
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        
        # Convert to Web Mercator
        county_cbg = county_cbg.to_crs('EPSG:3857')
        county_candidates = county_candidates.to_crs('EPSG:3857')
        
        # Left panel: Risk map with all candidates
        county_cbg.plot(
            column='risk',
            cmap='YlOrRd', 
            linewidth=0.2,
            edgecolor='white',
            alpha=0.7,
            ax=ax1
        )
        
        # Plot all candidate sites
        county_candidates.plot(
            ax=ax1,
            color='blue',
            markersize=15,
            alpha=0.6,
            marker='s'
        )
        
        ax1.set_title(f'All Candidate Sites\n{county_name}', fontsize=12, fontweight='bold')
        ax1.set_axis_off()
        
        # Right panel: Risk map with selected sites
        county_cbg.plot(
            column='risk',
            cmap='YlOrRd',
            linewidth=0.2, 
            edgecolor='white',
            alpha=0.7,
            ax=ax2,
            legend=True,
            legend_kwds={'shrink': 0.6}
        )
        
        # Plot selected sites
        if "site_metadata" in solution:
            selected_indices = [site["site_index"] for site in solution["site_metadata"]]
            selected_sites = county_candidates.iloc[selected_indices]
            
            selected_sites.plot(
                ax=ax2,
                color='red',
                markersize=60,
                marker='*',
                edgecolors='white',
                linewidth=2
            )
            
            # Add site labels
            for i, (idx, site) in enumerate(selected_sites.iterrows()):
                centroid = site.geometry.centroid
                ax2.annotate(
                    str(i + 1),
                    xy=(centroid.x, centroid.y),
                    xytext=(0, 0),
                    textcoords='offset points',
                    fontsize=10,
                    fontweight='bold',
                    ha='center',
                    va='center',
                    color='white'
                )
                
        ax2.set_title(f'Selected Resilience Hubs (K={K}, {scenario})\n'
                     f'Coverage: {solution["coverage_rate"]:.1%}',
                     fontsize=12, fontweight='bold')
        ax2.set_axis_off()
        
        # Add basemaps
        try:
            ctx.add_basemap(ax1, crs=county_cbg.crs, source=ctx.providers.CartoDB.Positron, alpha=0.3)
            ctx.add_basemap(ax2, crs=county_cbg.crs, source=ctx.providers.CartoDB.Positron, alpha=0.3)
        except Exception as e:
            print(f"Could not add basemaps: {e}")
            
        plt.tight_layout()
        return fig
        
    def create_pareto_chart(self, solution_data: Dict) -> plt.Figure:
        """Create Pareto frontier chart showing coverage vs K."""
        
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        
        scenarios = ["walk", "drive"]
        colors = {"walk": "#2E8B57", "drive": "#B22222"}
        
        for i, scenario in enumerate(scenarios):
            ax = axes[i]
            
            for county_name, county_solution in solution_data.items():
                if scenario not in county_solution:
                    continue
                    
                scenario_solution = county_solution[scenario]
                
                # Extract K values and coverage rates
                k_values = []
                coverage_rates = []
                
                for k_str, solution in scenario_solution.items():
                    if k_str.startswith("K_"):
                        k = int(k_str.split("_")[1])
                        coverage = solution["coverage_rate"]
                        
                        k_values.append(k)
                        coverage_rates.append(coverage * 100)  # Convert to percentage
                        
                # Sort by K
                sorted_data = sorted(zip(k_values, coverage_rates))
                k_values, coverage_rates = zip(*sorted_data) if sorted_data else ([], [])
                
                # Plot line
                if len(k_values) > 0:
                    ax.plot(k_values, coverage_rates, 
                           marker='o', linewidth=2, markersize=6,
                           label=county_name, alpha=0.8)
                    
            ax.set_xlabel('Number of Hubs (K)')
            ax.set_ylabel('Coverage Rate (%)')
            ax.set_title(f'{scenario.title()} Scenario (10 min)')
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.set_ylim(0, 100)
            
            # Add diminishing returns reference
            ax.axhline(y=80, color='red', linestyle='--', alpha=0.5, 
                      label='80% Coverage Target')
                      
        plt.suptitle('Coverage Rate vs Number of Hubs', fontsize=14, fontweight='bold')
        plt.tight_layout()
        return fig
        
    def create_component_analysis(self, cbg_gdf: gpd.GeoDataFrame) -> plt.Figure:
        """Create component analysis visualization."""
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        axes = axes.flatten()
        
        components = [
            ('risk', 'Composite Risk Index'),
            ('heat_exposure', 'Heat Exposure'),
            ('social_vulnerability', 'Social Vulnerability'), 
            ('digital_exclusion', 'Digital Exclusion'),
            ('elderly_vulnerability', 'Elderly Vulnerability')
        ]
        
        for i, (component, title) in enumerate(components):
            ax = axes[i]
            
            if component in cbg_gdf.columns:
                # Create choropleth for each county
                for county_name in cbg_gdf["county_name"].unique():
                    county_data = cbg_gdf[cbg_gdf["county_name"] == county_name]
                    
                    county_data.plot(
                        column=component,
                        cmap='YlOrRd',
                        linewidth=0.1,
                        edgecolor='white',
                        alpha=0.8,
                        ax=ax,
                        vmin=0,
                        vmax=1
                    )
                    
                ax.set_title(title, fontsize=12, fontweight='bold')
                ax.set_axis_off()
                
                # Add colorbar
                sm = cm.ScalarMappable(cmap='YlOrRd', norm=Normalize(vmin=0, vmax=1))
                sm.set_array([])
                cbar = plt.colorbar(sm, ax=ax, shrink=0.6, aspect=20)
                cbar.set_label('Score (0-1)', fontsize=10)
                
        # Use last subplot for legend/summary
        axes[5].axis('off')
        
        # Add component weights
        weights_text = """
        Component Weights:
        • Heat Exposure: 35%
        • Social Vulnerability: 30%
        • Digital Exclusion: 25%
        • Elderly Vulnerability: 10%
        """
        
        axes[5].text(0.1, 0.5, weights_text, fontsize=11, 
                    verticalalignment='center',
                    bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
                    
        plt.suptitle('Risk Index Components', fontsize=16, fontweight='bold')
        plt.tight_layout()
        return fig
        
    def generate_all_maps(self, output_dir: str = "data/out/figures"):
        """Generate all static maps for publication."""
        
        os.makedirs(output_dir, exist_ok=True)
        
        print("Loading data...")
        cbg_gdf, candidates_gdf = self.load_data()
        
        # Load solution data if available
        solution_path = "data/out/optimization_results_complete.json"
        solution_data = {}
        
        if os.path.exists(solution_path):
            with open(solution_path, 'r') as f:
                results = json.load(f)
                solution_data = results.get("optimization_results", {})
                
        counties = cbg_gdf["county_name"].unique()
        
        print(f"Generating maps for {len(counties)} counties...")
        
        # 1. Risk maps for each county
        for county_name in counties:
            print(f"Creating risk map for {county_name}...")
            
            fig = self.create_risk_map(cbg_gdf, county_name)
            
            county_safe = county_name.replace(" ", "_").replace(",", "")
            fig.savefig(f"{output_dir}/risk_map_{county_safe}.png", 
                       dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
        # 2. Component analysis
        print("Creating component analysis...")
        fig = self.create_component_analysis(cbg_gdf)
        fig.savefig(f"{output_dir}/component_analysis.png",
                   dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        
        # 3. Solution maps (if available)
        if solution_data:
            for county_name in counties:
                if county_name in solution_data:
                    print(f"Creating solution maps for {county_name}...")
                    
                    for scenario in ["walk", "drive"]:
                        try:
                            fig = self.create_solution_map(
                                cbg_gdf, candidates_gdf, solution_data,
                                county_name, scenario, K=10
                            )
                            
                            county_safe = county_name.replace(" ", "_").replace(",", "")
                            fig.savefig(f"{output_dir}/solution_map_{county_safe}_{scenario}.png",
                                       dpi=300, bbox_inches='tight', facecolor='white')
                            plt.close(fig)
                            
                        except Exception as e:
                            print(f"Could not create solution map for {county_name} {scenario}: {e}")
                            
            # 4. Pareto analysis
            print("Creating Pareto analysis...")
            fig = self.create_pareto_chart(solution_data)
            fig.savefig(f"{output_dir}/pareto_analysis.png",
                       dpi=300, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
        print(f"Maps saved to {output_dir}/")
        
        # Generate map inventory
        inventory = {
            "generated_maps": [],
            "timestamp": pd.Timestamp.now().isoformat()
        }
        
        for filename in os.listdir(output_dir):
            if filename.endswith('.png'):
                inventory["generated_maps"].append(filename)
                
        with open(f"{output_dir}/map_inventory.json", 'w') as f:
            json.dump(inventory, f, indent=2)
            
        print(f"Generated {len(inventory['generated_maps'])} maps")
        return inventory


def main():
    """Generate all static maps."""
    
    generator = StaticMapGenerator(style="paper")
    inventory = generator.generate_all_maps()
    
    print("\n=== Map Generation Complete ===")
    print(f"Generated {len(inventory['generated_maps'])} maps:")
    for filename in sorted(inventory['generated_maps']):
        print(f"  - {filename}")
        
    print("\nMaps are ready for inclusion in papers and reports.")


if __name__ == "__main__":
    main()