"""
Build coverage matrices for candidate sites.
"""
import networkx as nx
import geopandas as gpd
import pandas as pd
import numpy as np
import pickle
import os
from typing import Dict, List, Tuple
from collections import defaultdict
from shapely.geometry import Point
import json


class CoverageMatrixBuilder:
    """Build coverage matrices for MCLP optimization."""
    
    def __init__(self):
        """Initialize coverage builder."""
        pass
        
    def load_network(self, network_path: str) -> nx.MultiDiGraph:
        """Load network from pickle file."""
        with open(network_path, 'rb') as f:
            return pickle.load(f)
            
    def get_nearest_nodes(self, G: nx.MultiDiGraph, 
                         geometries: gpd.GeoSeries) -> List[int]:
        """Find nearest network nodes to geometries."""
        
        # Extract node coordinates
        node_data = []
        for node_id, data in G.nodes(data=True):
            node_data.append((node_id, data['x'], data['y']))
            
        if not node_data:
            return []
            
        node_df = pd.DataFrame(node_data, columns=['node_id', 'x', 'y'])
        node_coords = node_df[['x', 'y']].values
        
        nearest_nodes = []
        
        # Convert geometries to points if needed
        points = []
        for geom in geometries:
            if geom.geom_type == 'Point':
                points.append((geom.x, geom.y))
            else:
                # Use centroid for polygons
                centroid = geom.centroid
                points.append((centroid.x, centroid.y))
                
        points = np.array(points)
        
        # Find nearest node for each point
        for px, py in points:
            distances = np.sqrt((node_coords[:, 0] - px)**2 + 
                              (node_coords[:, 1] - py)**2)
            nearest_idx = np.argmin(distances)
            nearest_nodes.append(node_df.iloc[nearest_idx]['node_id'])
            
        return nearest_nodes
        
    def compute_travel_times(self, G: nx.MultiDiGraph, 
                           source_node: int) -> Dict[int, float]:
        """Compute travel times from source node to all reachable nodes."""
        try:
            # Use Dijkstra's algorithm with travel_time weights
            travel_times = nx.single_source_dijkstra_path_length(
                G, source_node, weight='travel_time'
            )
            return travel_times
        except Exception as e:
            print(f"Error computing travel times from node {source_node}: {e}")
            return {}
            
    def build_coverage_matrix(self, 
                            demand_nodes: List[int],
                            supply_nodes: List[int], 
                            G: nx.MultiDiGraph,
                            max_travel_time_min: float = 10) -> Dict[int, List[int]]:
        """
        Build coverage matrix A[i][j] = 1 if site j covers demand i.
        
        Args:
            demand_nodes: Network nodes for demand points (CBG centroids)
            supply_nodes: Network nodes for candidate sites
            G: Transportation network
            max_travel_time_min: Maximum travel time in minutes
            
        Returns:
            Coverage dictionary: demand_idx -> list of covering site indices
        """
        max_travel_time_sec = max_travel_time_min * 60
        
        print(f"Building coverage matrix: {len(demand_nodes)} demand, {len(supply_nodes)} supply")
        print(f"Max travel time: {max_travel_time_min} minutes")
        
        coverage = defaultdict(list)
        
        # For each supply node, find which demand nodes it can cover
        for site_idx, supply_node in enumerate(supply_nodes):
            if site_idx % 10 == 0:
                print(f"Processing site {site_idx+1}/{len(supply_nodes)}")
                
            # Compute travel times from this supply node
            travel_times = self.compute_travel_times(G, supply_node)
            
            # Check which demand nodes are within time threshold
            for demand_idx, demand_node in enumerate(demand_nodes):
                travel_time = travel_times.get(demand_node, float('inf'))
                
                if travel_time <= max_travel_time_sec:
                    coverage[demand_idx].append(site_idx)
                    
        print(f"Coverage matrix built: avg {np.mean([len(sites) for sites in coverage.values()]):.1f} sites per demand")
        
        return dict(coverage)
        
    def process_county_coverage(self, 
                              county_name: str,
                              cbg_gdf: gpd.GeoDataFrame,
                              candidates_gdf: gpd.GeoDataFrame) -> Dict[str, Dict]:
        """Process coverage matrices for a county."""
        
        print(f"\nProcessing coverage for {county_name}...")
        
        # Filter data to county
        county_cbg = cbg_gdf[cbg_gdf["county_name"] == county_name].copy()
        county_candidates = candidates_gdf[candidates_gdf["county_name"] == county_name].copy()
        
        print(f"County data: {len(county_cbg)} CBGs, {len(county_candidates)} candidates")
        
        if len(county_cbg) == 0 or len(county_candidates) == 0:
            print("No data for county, skipping...")
            return {}
            
        # Load networks
        network_dir = f"data/int/networks/{county_name.replace(' ', '_').replace(',', '')}"
        
        county_coverage = {}
        
        for network_type in ["walk", "drive"]:
            network_path = f"{network_dir}/{network_type}_network.pkl"
            
            if not os.path.exists(network_path):
                print(f"Network not found: {network_path}, skipping...")
                continue
                
            print(f"Loading {network_type} network...")
            G = self.load_network(network_path)
            
            # Get nearest network nodes
            print("Finding nearest nodes...")
            demand_nodes = self.get_nearest_nodes(G, county_cbg.geometry)
            supply_nodes = self.get_nearest_nodes(G, county_candidates.geometry)
            
            # Build coverage matrix
            coverage_matrix = self.build_coverage_matrix(
                demand_nodes, supply_nodes, G, max_travel_time_min=10
            )
            
            # Store results with metadata
            coverage_data = {
                "coverage_matrix": coverage_matrix,
                "demand_metadata": {
                    "geoids": county_cbg["GEOID"].tolist(),
                    "demand_weights": county_cbg["demand_weight"].tolist(),
                    "risk_scores": county_cbg["risk"].tolist(),
                    "network_nodes": demand_nodes
                },
                "supply_metadata": {
                    "site_ids": county_candidates.index.tolist(),
                    "amenity_types": county_candidates["amenity"].tolist(),
                    "site_names": county_candidates["name"].tolist(),
                    "footprint_areas": county_candidates["footprint_area_m2"].tolist(),
                    "network_nodes": supply_nodes
                },
                "network_stats": {
                    "nodes": len(G.nodes),
                    "edges": len(G.edges),
                    "max_travel_time_min": 10
                }
            }
            
            county_coverage[network_type] = coverage_data
            
        return county_coverage
        
    def save_coverage_data(self, coverage_data: Dict, output_path: str):
        """Save coverage data to JSON file."""
        
        # Convert numpy types for JSON serialization
        def convert_numpy(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
            
        # Deep convert the data
        json_data = json.loads(json.dumps(coverage_data, default=convert_numpy))
        
        with open(output_path, 'w') as f:
            json.dump(json_data, f, indent=2)
            
    def process_all_counties(self, 
                           cbg_gdf: gpd.GeoDataFrame,
                           candidates_gdf: gpd.GeoDataFrame) -> Dict[str, Dict]:
        """Process coverage matrices for all counties."""
        
        all_coverage = {}
        
        counties = cbg_gdf["county_name"].unique()
        
        for county_name in counties:
            county_coverage = self.process_county_coverage(
                county_name, cbg_gdf, candidates_gdf
            )
            
            if county_coverage:
                all_coverage[county_name] = county_coverage
                
                # Save individual county data
                county_safe_name = county_name.replace(' ', '_').replace(',', '')
                output_path = f"data/int/coverage_{county_safe_name}.json"
                self.save_coverage_data(county_coverage, output_path)
                
                print(f"Saved coverage data to {output_path}")
                
        return all_coverage
        
    def generate_coverage_summary(self, all_coverage: Dict) -> Dict:
        """Generate summary statistics for coverage matrices."""
        
        summary = {
            "counties": {},
            "overall": {}
        }
        
        total_demand_points = 0
        total_supply_points = 0
        total_coverage_links = 0
        
        for county_name, county_coverage in all_coverage.items():
            county_stats = {"scenarios": {}}
            
            for scenario, coverage_data in county_coverage.items():
                matrix = coverage_data["coverage_matrix"]
                n_demand = len(coverage_data["demand_metadata"]["geoids"])
                n_supply = len(coverage_data["supply_metadata"]["site_ids"])
                
                # Coverage statistics
                covered_demand = len([i for i, sites in matrix.items() if len(sites) > 0])
                avg_options = np.mean([len(sites) for sites in matrix.values()])
                total_links = sum(len(sites) for sites in matrix.values())
                
                scenario_stats = {
                    "demand_points": n_demand,
                    "supply_points": n_supply, 
                    "covered_demand_points": covered_demand,
                    "coverage_rate": covered_demand / n_demand if n_demand > 0 else 0,
                    "avg_supply_options": avg_options,
                    "total_coverage_links": total_links
                }
                
                county_stats["scenarios"][scenario] = scenario_stats
                
            summary["counties"][county_name] = county_stats
            
            # Add to totals (use walk scenario for counting)
            if "walk" in county_coverage:
                walk_data = county_coverage["walk"]
                total_demand_points += len(walk_data["demand_metadata"]["geoids"])
                total_supply_points += len(walk_data["supply_metadata"]["site_ids"])
                total_coverage_links += sum(len(sites) for sites in walk_data["coverage_matrix"].values())
                
        summary["overall"] = {
            "total_counties": len(all_coverage),
            "total_demand_points": total_demand_points,
            "total_supply_points": total_supply_points,
            "total_coverage_links": total_coverage_links
        }
        
        return summary


def main():
    """Build coverage matrices."""
    
    # Load data
    cbg_path = "data/out/cbg_with_risk_index.geojson"
    candidates_path = "data/int/candidate_sites.geojson"
    
    if not os.path.exists(cbg_path):
        print(f"CBG file not found: {cbg_path}")
        return
        
    if not os.path.exists(candidates_path):
        print(f"Candidates file not found: {candidates_path}")
        return
        
    print("Loading data...")
    cbg_gdf = gpd.read_file(cbg_path)
    candidates_gdf = gpd.read_file(candidates_path)
    
    print(f"Loaded {len(cbg_gdf)} CBGs and {len(candidates_gdf)} candidate sites")
    
    # Build coverage matrices
    builder = CoverageMatrixBuilder()
    all_coverage = builder.process_all_counties(cbg_gdf, candidates_gdf)
    
    # Generate summary
    summary = builder.generate_coverage_summary(all_coverage)
    
    # Save summary
    summary_path = "data/int/coverage_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
        
    print(f"\nCoverage matrix processing complete!")
    print(f"Summary saved to {summary_path}")
    
    print("\n=== Coverage Summary ===")
    print(f"Counties processed: {summary['overall']['total_counties']}")
    print(f"Total demand points: {summary['overall']['total_demand_points']}")
    print(f"Total supply points: {summary['overall']['total_supply_points']}")
    print(f"Total coverage links: {summary['overall']['total_coverage_links']}")
    
    for county_name, county_stats in summary["counties"].items():
        print(f"\n{county_name}:")
        for scenario, stats in county_stats["scenarios"].items():
            print(f"  {scenario}: {stats['coverage_rate']:.1%} coverage, "
                  f"{stats['avg_supply_options']:.1f} avg options")


if __name__ == "__main__":
    main()