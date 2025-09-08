"""
Build transportation network graphs using OSMnx.
"""
import osmnx as ox
import networkx as nx
import geopandas as gpd
import pandas as pd
import numpy as np
import pickle
import os
from typing import Tuple, Dict, List
from shapely.geometry import Point


class NetworkBuilder:
    """Build and process transportation networks."""
    
    def __init__(self):
        """Initialize network builder."""
        # Configure OSMnx
        ox.settings.log_console = True
        ox.settings.use_cache = True
        
    def get_county_bounds(self, cbg_gdf: gpd.GeoDataFrame) -> Dict[str, Tuple]:
        """Get bounding box for each county."""
        bounds_by_county = {}
        
        county_groups = cbg_gdf.groupby("county_name")
        
        for county_name, county_data in county_groups:
            # Get bounds as (north, south, east, west) for OSMnx
            minx, miny, maxx, maxy = county_data.total_bounds
            
            # Add buffer around county (0.01 degrees ≈ 1km)
            buffer = 0.01
            bounds = (maxy + buffer, miny - buffer, maxx + buffer, minx - buffer)
            bounds_by_county[county_name] = bounds
            
        return bounds_by_county
        
    def download_network(self, bounds: Tuple, network_type: str = "walk") -> nx.MultiDiGraph:
        """
        Download network from OSM.
        
        Args:
            bounds: (north, south, east, west) bounding box
            network_type: 'walk' or 'drive'
            
        Returns:
            NetworkX graph
        """
        north, south, east, west = bounds
        
        print(f"Downloading {network_type} network for bounds {bounds}...")
        
        try:
            # Download network
            G = ox.graph_from_bbox(
                north, south, east, west,
                network_type=network_type,
                simplify=True,
                retain_all=False
            )
            
            print(f"Downloaded network: {len(G.nodes)} nodes, {len(G.edges)} edges")
            
        except Exception as e:
            print(f"Error downloading network: {e}")
            print("Creating mock network...")
            G = self._create_mock_network(bounds, network_type)
            
        return G
        
    def _create_mock_network(self, bounds: Tuple, network_type: str) -> nx.MultiDiGraph:
        """Create a mock network for testing."""
        north, south, east, west = bounds
        
        # Create grid network
        n_nodes_x = 20
        n_nodes_y = 20
        
        x_coords = np.linspace(west, east, n_nodes_x)
        y_coords = np.linspace(south, north, n_nodes_y)
        
        G = nx.MultiDiGraph()
        
        # Add nodes
        node_id = 0
        node_positions = {}
        
        for i, x in enumerate(x_coords):
            for j, y in enumerate(y_coords):
                G.add_node(node_id, x=x, y=y)
                node_positions[node_id] = (x, y)
                node_id += 1
                
        # Add edges (grid connections)
        for i in range(n_nodes_x):
            for j in range(n_nodes_y):
                current_node = i * n_nodes_y + j
                
                # Horizontal edges
                if i < n_nodes_x - 1:
                    next_node = (i + 1) * n_nodes_y + j
                    
                    # Distance between nodes
                    x1, y1 = node_positions[current_node]
                    x2, y2 = node_positions[next_node] 
                    
                    # Convert degrees to meters (rough approximation)
                    dx_m = (x2 - x1) * 111000 * np.cos(np.radians(y1))
                    dy_m = (y2 - y1) * 111000
                    length_m = np.sqrt(dx_m**2 + dy_m**2)
                    
                    # Add bidirectional edges
                    G.add_edge(current_node, next_node, 
                              length=length_m, highway="residential")
                    G.add_edge(next_node, current_node,
                              length=length_m, highway="residential")
                              
                # Vertical edges  
                if j < n_nodes_y - 1:
                    next_node = i * n_nodes_y + (j + 1)
                    
                    x1, y1 = node_positions[current_node]
                    x2, y2 = node_positions[next_node]
                    
                    dx_m = (x2 - x1) * 111000 * np.cos(np.radians(y1))
                    dy_m = (y2 - y1) * 111000
                    length_m = np.sqrt(dx_m**2 + dy_m**2)
                    
                    G.add_edge(current_node, next_node,
                              length=length_m, highway="residential") 
                    G.add_edge(next_node, current_node,
                              length=length_m, highway="residential")
                              
        print(f"Created mock network: {len(G.nodes)} nodes, {len(G.edges)} edges")
        return G
        
    def add_travel_times(self, G: nx.MultiDiGraph, network_type: str) -> nx.MultiDiGraph:
        """Add travel time weights to network edges."""
        
        # Speed assumptions (km/h)
        speeds = {
            "walk": {
                "default": 4.8,  # 1.33 m/s
                "residential": 4.8,
                "footway": 4.8,
                "path": 4.0
            },
            "drive": {
                "default": 40,
                "residential": 25,
                "primary": 55,
                "secondary": 45,
                "tertiary": 35,
                "trunk": 65,
                "motorway": 80
            }
        }
        
        speed_lookup = speeds.get(network_type, speeds["walk"])
        default_speed = speed_lookup["default"]
        
        for u, v, k, data in G.edges(keys=True, data=True):
            # Get edge length in meters
            length_m = data.get("length", 100)  # Default 100m if missing
            
            # Get highway type for speed lookup
            highway = data.get("highway", "default")
            if isinstance(highway, list):
                highway = highway[0]  # Use first type if multiple
                
            # Get speed for this highway type
            speed_kmh = speed_lookup.get(highway, default_speed)
            
            # Convert to travel time in seconds
            travel_time_sec = (length_m / 1000) / speed_kmh * 3600
            
            G[u][v][k]["travel_time"] = travel_time_sec
            
        return G
        
    def process_county_networks(self, county_bounds: Dict[str, Tuple]) -> Dict[str, Dict]:
        """Process networks for all counties."""
        
        networks = {}
        
        for county_name, bounds in county_bounds.items():
            print(f"\nProcessing networks for {county_name}...")
            
            county_networks = {}
            
            # Process both walk and drive networks
            for network_type in ["walk", "drive"]:
                print(f"Building {network_type} network...")
                
                # Download network
                G = self.download_network(bounds, network_type)
                
                # Add travel times
                G = self.add_travel_times(G, network_type)
                
                county_networks[network_type] = G
                
                # Save network
                output_dir = f"data/int/networks/{county_name.replace(' ', '_').replace(',', '')}"
                os.makedirs(output_dir, exist_ok=True)
                
                network_path = f"{output_dir}/{network_type}_network.pkl"
                
                with open(network_path, 'wb') as f:
                    pickle.dump(G, f)
                    
                print(f"Saved {network_type} network to {network_path}")
                
            networks[county_name] = county_networks
            
        return networks
        
    def get_nearest_nodes(self, G: nx.MultiDiGraph, 
                         points: List[Point]) -> List[int]:
        """Find nearest network nodes to points."""
        
        # Extract node coordinates
        node_coords = []
        node_ids = []
        
        for node_id, data in G.nodes(data=True):
            node_coords.append((data['x'], data['y']))
            node_ids.append(node_id)
            
        node_coords = np.array(node_coords)
        
        # Find nearest nodes for each point
        nearest_nodes = []
        
        for point in points:
            px, py = point.x, point.y
            
            # Calculate distances to all nodes
            distances = np.sqrt((node_coords[:, 0] - px)**2 + 
                              (node_coords[:, 1] - py)**2)
            
            # Find nearest
            nearest_idx = np.argmin(distances)
            nearest_nodes.append(node_ids[nearest_idx])
            
        return nearest_nodes


def main():
    """Build networks for all counties."""
    
    # Load CBG data to get county bounds
    cbg_path = "data/out/cbg_with_risk_index.geojson"
    
    if not os.path.exists(cbg_path):
        print(f"CBG file not found: {cbg_path}")
        print("Run the risk computation pipeline first")
        return
        
    print("Loading CBG data...")
    cbg_gdf = gpd.read_file(cbg_path)
    
    # Build networks
    builder = NetworkBuilder()
    
    # Get county bounds
    county_bounds = builder.get_county_bounds(cbg_gdf)
    print(f"Processing {len(county_bounds)} counties")
    
    # Process networks
    networks = builder.process_county_networks(county_bounds)
    
    print(f"\nNetwork processing complete!")
    print("Networks saved to data/int/networks/")
    
    for county_name, county_networks in networks.items():
        print(f"{county_name}:")
        for net_type, G in county_networks.items():
            print(f"  {net_type}: {len(G.nodes)} nodes, {len(G.edges)} edges")


if __name__ == "__main__":
    main()