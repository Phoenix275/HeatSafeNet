"""
Solve optimization scenarios and generate comprehensive results.
"""
import json
import os
import pandas as pd
import geopandas as gpd
import numpy as np
from typing import Dict, List, Tuple
import time
from .mclp_solver import MCLPSolver


class ScenarioSolver:
    """Solve and analyze multiple optimization scenarios."""
    
    def __init__(self):
        """Initialize scenario solver."""
        self.solver = MCLPSolver()
        
    def load_all_coverage_data(self) -> Dict[str, Dict]:
        """Load coverage data for all counties."""
        coverage_data = {}
        
        coverage_dir = "data/int"
        
        for filename in os.listdir(coverage_dir):
            if filename.startswith("coverage_") and filename.endswith(".json"):
                county_part = filename[9:-5]  # Remove "coverage_" and ".json"
                
                filepath = os.path.join(coverage_dir, filename)
                print(f"Loading {filepath}...")
                
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    
                # Extract readable county name
                if "Harris_County_TX" in county_part:
                    county_name = "Harris County, TX"
                elif "Maricopa_County_AZ" in county_part:
                    county_name = "Maricopa County, AZ"
                else:
                    county_name = county_part.replace('_', ' ')
                    
                coverage_data[county_name] = data
                
        return coverage_data
        
    def solve_all_scenarios(self, 
                          coverage_data: Dict[str, Dict],
                          K_values: List[int] = [5, 10, 20],
                          scenarios: List[str] = ["walk", "drive"]) -> Dict[str, Dict]:
        """Solve optimization for all counties and scenarios."""
        
        all_results = {}
        
        print(f"Solving optimization for {len(coverage_data)} counties...")
        print(f"K values: {K_values}")
        print(f"Scenarios: {scenarios}")
        
        for county_name, county_coverage in coverage_data.items():
            print(f"\n{'='*50}")
            print(f"Processing {county_name}")
            print(f"{'='*50}")
            
            county_results = self.solver.solve_multiple_scenarios(
                county_coverage, K_values, scenarios
            )
            
            all_results[county_name] = county_results
            
        return all_results
        
    def analyze_results(self, results: Dict[str, Dict]) -> Dict:
        """Analyze optimization results across counties and scenarios."""
        
        analysis = {
            "summary": {},
            "by_county": {},
            "by_scenario": {},
            "pareto_analysis": {}
        }
        
        # Overall summary
        total_counties = len(results)
        all_k_values = set()
        all_scenarios = set()
        
        for county_results in results.values():
            all_scenarios.update(county_results.keys())
            for scenario_results in county_results.values():
                all_k_values.update(scenario_results.keys())
                
        analysis["summary"] = {
            "total_counties": total_counties,
            "scenarios": sorted(list(all_scenarios)),
            "k_values": sorted([int(k.split('_')[1]) for k in all_k_values]),
            "total_solutions": sum(
                len(scenario_results) * len(county_results)
                for county_results in results.values()
                for scenario_results in county_results.values()
            )
        }
        
        # Analysis by county
        for county_name, county_results in results.items():
            county_analysis = {}
            
            for scenario, scenario_results in county_results.items():
                scenario_analysis = {}
                
                # Extract key metrics for each K
                k_metrics = {}
                for k_str, solution in scenario_results.items():
                    k_val = int(k_str.split('_')[1])
                    
                    k_metrics[k_val] = {
                        "sites_selected": solution["num_sites_selected"],
                        "coverage_rate": solution["coverage_rate"],
                        "covered_demand": solution["covered_demand_points"],
                        "total_weight": solution["total_covered_weight"],
                        "solve_time": solution["solve_time_sec"]
                    }
                    
                # Calculate efficiency metrics
                k_sorted = sorted(k_metrics.keys())
                if len(k_sorted) > 1:
                    marginal_benefits = []
                    for i in range(1, len(k_sorted)):
                        prev_k = k_sorted[i-1]
                        curr_k = k_sorted[i]
                        
                        weight_gain = k_metrics[curr_k]["total_weight"] - k_metrics[prev_k]["total_weight"]
                        k_increase = curr_k - prev_k
                        
                        marginal_benefit = weight_gain / k_increase if k_increase > 0 else 0
                        marginal_benefits.append({
                            "from_k": prev_k,
                            "to_k": curr_k,
                            "marginal_benefit": marginal_benefit
                        })
                        
                    scenario_analysis["marginal_benefits"] = marginal_benefits
                    
                scenario_analysis["k_metrics"] = k_metrics
                county_analysis[scenario] = scenario_analysis
                
            analysis["by_county"][county_name] = county_analysis
            
        # Analysis by scenario (cross-county)
        for scenario in all_scenarios:
            scenario_summary = {
                "counties_with_data": 0,
                "avg_coverage_by_k": {},
                "best_counties": {},
                "efficiency_comparison": []
            }
            
            k_coverage_data = {}
            
            for county_name, county_results in results.items():
                if scenario in county_results:
                    scenario_summary["counties_with_data"] += 1
                    
                    for k_str, solution in county_results[scenario].items():
                        k_val = int(k_str.split('_')[1])
                        
                        if k_val not in k_coverage_data:
                            k_coverage_data[k_val] = []
                            
                        k_coverage_data[k_val].append({
                            "county": county_name,
                            "coverage_rate": solution["coverage_rate"],
                            "total_weight": solution["total_covered_weight"]
                        })
                        
            # Calculate averages
            for k_val, county_data in k_coverage_data.items():
                avg_coverage = np.mean([d["coverage_rate"] for d in county_data])
                scenario_summary["avg_coverage_by_k"][k_val] = avg_coverage
                
                # Find best performing county
                best_county = max(county_data, key=lambda x: x["coverage_rate"])
                scenario_summary["best_counties"][k_val] = best_county
                
            analysis["by_scenario"][scenario] = scenario_summary
            
        # Pareto analysis (coverage vs. number of sites)
        pareto_data = []
        
        for county_name, county_results in results.items():
            for scenario, scenario_results in county_results.items():
                for k_str, solution in scenario_results.items():
                    k_val = int(k_str.split('_')[1])
                    
                    pareto_data.append({
                        "county": county_name,
                        "scenario": scenario, 
                        "k": k_val,
                        "coverage_rate": solution["coverage_rate"],
                        "total_weight": solution["total_covered_weight"],
                        "sites_selected": solution["num_sites_selected"]
                    })
                    
        analysis["pareto_analysis"]["raw_data"] = pareto_data
        
        # Find pareto frontier for each scenario
        for scenario in all_scenarios:
            scenario_data = [d for d in pareto_data if d["scenario"] == scenario]
            
            if scenario_data:
                # Sort by K value
                scenario_data.sort(key=lambda x: x["k"])
                
                # Calculate efficiency metrics
                efficiency_metrics = []
                for i, point in enumerate(scenario_data):
                    if i == 0:
                        marginal_coverage = point["coverage_rate"]
                        marginal_sites = point["sites_selected"]
                    else:
                        marginal_coverage = point["coverage_rate"] - scenario_data[i-1]["coverage_rate"]
                        marginal_sites = point["sites_selected"] - scenario_data[i-1]["sites_selected"]
                        
                    efficiency = marginal_coverage / marginal_sites if marginal_sites > 0 else 0
                    
                    efficiency_metrics.append({
                        "k": point["k"],
                        "marginal_coverage_per_site": efficiency,
                        "diminishing_returns": efficiency < 0.01 if i > 0 else False
                    })
                    
                analysis["pareto_analysis"][f"{scenario}_efficiency"] = efficiency_metrics
                
        return analysis
        
    def generate_site_recommendations(self, results: Dict[str, Dict], 
                                   cbg_gdf: gpd.GeoDataFrame,
                                   candidates_gdf: gpd.GeoDataFrame) -> Dict:
        """Generate detailed site recommendations."""
        
        recommendations = {}
        
        for county_name, county_results in results.items():
            county_recommendations = {}
            
            # Filter data to county
            county_cbg = cbg_gdf[cbg_gdf["county_name"] == county_name]
            county_candidates = candidates_gdf[candidates_gdf["county_name"] == county_name]
            
            for scenario, scenario_results in county_results.items():
                scenario_recommendations = {}
                
                for k_str, solution in scenario_results.items():
                    if "site_metadata" not in solution:
                        continue
                        
                    k_val = int(k_str.split('_')[1])
                    
                    # Get selected sites with enhanced metadata
                    selected_sites = []
                    
                    for site_info in solution["site_metadata"]:
                        site_idx = site_info["site_index"]
                        
                        # Get full candidate info
                        if site_idx < len(county_candidates):
                            candidate = county_candidates.iloc[site_idx]
                            
                            enhanced_site = {
                                "rank": len(selected_sites) + 1,
                                "site_index": site_idx,
                                "name": site_info["name"],
                                "amenity": site_info["amenity"],
                                "footprint_area_m2": site_info["footprint_area_m2"],
                                "address": f"{candidate.get('addr_street', '')}, {candidate.get('addr_city', '')}".strip(', '),
                                "coordinates": {
                                    "lat": candidate.geometry.y,
                                    "lon": candidate.geometry.x
                                },
                                "suitability_score": self._calculate_site_suitability(candidate),
                                "constraints": self._check_site_constraints(candidate)
                            }
                            
                            selected_sites.append(enhanced_site)
                            
                    scenario_recommendations[k_val] = {
                        "solution_summary": {
                            "sites_selected": solution["num_sites_selected"],
                            "coverage_rate": solution["coverage_rate"],
                            "covered_population": solution["covered_demand_points"],
                            "total_weighted_coverage": solution["total_covered_weight"]
                        },
                        "recommended_sites": selected_sites[:15]  # Top 15 for reporting
                    }
                    
                county_recommendations[scenario] = scenario_recommendations
                
            recommendations[county_name] = county_recommendations
            
        return recommendations
        
    def _calculate_site_suitability(self, candidate_row) -> float:
        """Calculate a suitability score for a site."""
        score = 0.5  # Base score
        
        # Amenity type preferences
        amenity_scores = {
            "school": 0.9,
            "library": 0.9, 
            "community_centre": 0.85,
            "place_of_worship": 0.7,
            "hospital": 0.6  # May have capacity constraints
        }
        
        amenity = candidate_row.get("amenity", "unknown")
        score = amenity_scores.get(amenity, 0.5)
        
        # Size factor (larger buildings are better)
        footprint = candidate_row.get("footprint_area_m2", 1000)
        if footprint > 2000:
            score += 0.1
        elif footprint < 500:
            score -= 0.1
            
        return min(1.0, max(0.0, score))
        
    def _check_site_constraints(self, candidate_row) -> Dict:
        """Check constraints for a site."""
        constraints = {
            "flood_risk": "unknown",  # Would check against flood zones
            "min_size_met": candidate_row.get("footprint_area_m2", 1000) >= 300,
            "broadband_available": "unknown"  # Would check FCC data
        }
        
        return constraints
        
    def run_full_analysis(self) -> Dict:
        """Run complete optimization analysis pipeline."""
        
        print("Starting comprehensive optimization analysis...")
        
        # Load data
        print("\n1. Loading coverage data...")
        coverage_data = self.load_all_coverage_data()
        
        if not coverage_data:
            print("No coverage data found. Run network analysis first.")
            return {}
            
        # Solve optimization scenarios
        print("\n2. Solving optimization scenarios...")
        results = self.solve_all_scenarios(coverage_data)
        
        # Analyze results
        print("\n3. Analyzing results...")
        analysis = self.analyze_results(results)
        
        # Load spatial data for recommendations
        cbg_path = "data/out/cbg_with_risk_index.geojson"
        candidates_path = "data/int/candidate_sites.geojson"
        
        recommendations = {}
        if os.path.exists(cbg_path) and os.path.exists(candidates_path):
            print("\n4. Generating site recommendations...")
            cbg_gdf = gpd.read_file(cbg_path)
            candidates_gdf = gpd.read_file(candidates_path)
            
            recommendations = self.generate_site_recommendations(
                results, cbg_gdf, candidates_gdf
            )
            
        # Compile final results
        final_results = {
            "optimization_results": results,
            "analysis": analysis, 
            "recommendations": recommendations,
            "metadata": {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "solver_type": self.solver.solver_type,
                "total_counties": len(coverage_data),
                "scenarios_solved": analysis["summary"]["scenarios"],
                "k_values_tested": analysis["summary"]["k_values"]
            }
        }
        
        return final_results


def main():
    """Run optimization scenario analysis."""
    
    # Run full analysis
    solver = ScenarioSolver()
    results = solver.run_full_analysis()
    
    if not results:
        return
        
    # Save results
    output_path = "data/out/optimization_results_complete.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
        
    print(f"\nComplete optimization results saved to {output_path}")
    
    # Print summary
    analysis = results["analysis"]
    print(f"\n{'='*60}")
    print("OPTIMIZATION SUMMARY")
    print(f"{'='*60}")
    print(f"Counties processed: {analysis['summary']['total_counties']}")
    print(f"Scenarios: {', '.join(analysis['summary']['scenarios'])}")
    print(f"K values tested: {analysis['summary']['k_values']}")
    print(f"Total solutions: {analysis['summary']['total_solutions']}")
    
    print(f"\nAverage coverage rates by scenario (K=10):")
    for scenario, scenario_data in analysis["by_scenario"].items():
        if 10 in scenario_data["avg_coverage_by_k"]:
            avg_cov = scenario_data["avg_coverage_by_k"][10]
            print(f"  {scenario}: {avg_cov:.1%}")
            
    print(f"\nBest performing counties (K=10):")
    for scenario, scenario_data in analysis["by_scenario"].items():
        if 10 in scenario_data["best_counties"]:
            best = scenario_data["best_counties"][10]
            print(f"  {scenario}: {best['county']} ({best['coverage_rate']:.1%} coverage)")


if __name__ == "__main__":
    main()