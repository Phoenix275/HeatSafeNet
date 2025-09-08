"""
Maximal Covering Location Problem (MCLP) solver.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import json
import time


class MCLPSolver:
    """Solve MCLP using OR-Tools or PuLP."""
    
    def __init__(self, solver_type: str = "ortools"):
        """
        Initialize MCLP solver.
        
        Args:
            solver_type: "ortools" or "pulp"
        """
        self.solver_type = solver_type
        self._initialize_solver()
        
    def _initialize_solver(self):
        """Initialize the chosen solver library."""
        if self.solver_type == "ortools":
            try:
                from ortools.linear_solver import pywraplp
                self.solver_lib = pywraplp
                self.available = True
                print("Using OR-Tools solver")
            except ImportError:
                print("OR-Tools not available, falling back to PuLP")
                self._initialize_pulp()
        else:
            self._initialize_pulp()
            
    def _initialize_pulp(self):
        """Initialize PuLP solver."""
        try:
            import pulp
            self.solver_lib = pulp
            self.solver_type = "pulp"
            self.available = True
            print("Using PuLP solver")
        except ImportError:
            print("Neither OR-Tools nor PuLP available, using greedy heuristic")
            self.solver_type = "greedy"
            self.available = False
            
    def solve_mclp_ortools(self, 
                          coverage_matrix: Dict[int, List[int]],
                          demand_weights: List[float],
                          K: int,
                          equity_constraint: bool = False,
                          equity_threshold: float = 0.6) -> Tuple[List[int], float, Dict]:
        """
        Solve MCLP using OR-Tools.
        
        Args:
            coverage_matrix: demand_idx -> list of covering site indices  
            demand_weights: Weight for each demand point
            K: Number of sites to select
            equity_constraint: Add equity constraint for high-risk areas
            equity_threshold: Minimum share of high-risk demand to cover
            
        Returns:
            (selected_sites, objective_value, solution_info)
        """
        from ortools.linear_solver import pywraplp
        
        # Create solver
        solver = pywraplp.Solver.CreateSolver("CBC")
        if not solver:
            raise RuntimeError("CBC solver not available")
            
        # Problem dimensions
        num_demand = len(demand_weights)
        all_sites = set()
        for sites in coverage_matrix.values():
            # Convert site IDs to integers if they're strings
            for site in sites:
                if isinstance(site, str) and site.isdigit():
                    all_sites.add(int(site))
                else:
                    all_sites.add(site)
        all_sites = sorted(list(all_sites))
        num_sites = len(all_sites)
        
        print(f"MCLP problem: {num_demand} demand points, {num_sites} candidate sites, K={K}")
        
        # Decision variables
        x = {}  # x[i] = 1 if demand i is covered
        y = {}  # y[j] = 1 if site j is selected
        
        for i in range(num_demand):
            x[i] = solver.BoolVar(f"x_{i}")
            
        for j in all_sites:
            y[j] = solver.BoolVar(f"y_{j}")
            
        # Objective: maximize weighted covered demand
        objective = solver.Objective()
        for i in range(num_demand):
            objective.SetCoefficient(x[i], demand_weights[i])
        objective.SetMaximization()
        
        # Constraint 1: Budget constraint (select at most K sites)
        budget_constraint = solver.Constraint(0, K)
        for j in all_sites:
            budget_constraint.SetCoefficient(y[j], 1)
            
        # Constraint 2: Coverage constraints
        for i, covering_sites in coverage_matrix.items():
            # Convert string keys to integers if needed
            demand_idx = int(i) if isinstance(i, str) and i.isdigit() else i
            if demand_idx < num_demand:  # Ensure valid demand index
                coverage_constraint = solver.Constraint(0, solver.infinity())
                coverage_constraint.SetCoefficient(x[demand_idx], -1)  # -x[i]
                for j in covering_sites:
                    if j in all_sites:
                        coverage_constraint.SetCoefficient(y[j], 1)  # +y[j]
                        
        # Optional: Equity constraint
        if equity_constraint:
            # Assume high-risk demand points are those with top 25% demand weights
            weight_threshold = np.percentile(demand_weights, 75)
            high_risk_indices = [i for i, w in enumerate(demand_weights) if w >= weight_threshold]
            
            if high_risk_indices:
                total_high_risk_weight = sum(demand_weights[i] for i in high_risk_indices)
                min_high_risk_coverage = equity_threshold * total_high_risk_weight
                
                equity_constraint = solver.Constraint(min_high_risk_coverage, solver.infinity())
                for i in high_risk_indices:
                    equity_constraint.SetCoefficient(x[i], demand_weights[i])
                    
                print(f"Added equity constraint: cover ≥{equity_threshold:.1%} of high-risk demand")
                
        # Solve
        print("Solving MCLP...")
        start_time = time.time()
        status = solver.Solve()
        solve_time = time.time() - start_time
        
        # Extract solution
        if status == pywraplp.Solver.OPTIMAL:
            selected_sites = [j for j in all_sites if y[j].solution_value() > 0.5]
            objective_value = solver.Objective().Value()
            
            # Calculate coverage statistics
            covered_demand = [i for i in range(num_demand) if x[i].solution_value() > 0.5]
            total_covered_weight = sum(demand_weights[i] for i in covered_demand)
            
            solution_info = {
                "status": "optimal",
                "objective_value": objective_value,
                "selected_sites": selected_sites,
                "num_sites_selected": len(selected_sites),
                "covered_demand_points": len(covered_demand),
                "total_covered_weight": total_covered_weight,
                "coverage_rate": len(covered_demand) / num_demand,
                "solve_time_sec": solve_time
            }
            
            print(f"Optimal solution found: {len(selected_sites)} sites, "
                  f"coverage={len(covered_demand)}/{num_demand} ({len(covered_demand)/num_demand:.1%})")
                  
        else:
            print(f"Solver status: {status}")
            selected_sites = []
            objective_value = 0
            solution_info = {
                "status": "infeasible_or_unbounded",
                "solve_time_sec": solve_time
            }
            
        return selected_sites, objective_value, solution_info
        
    def solve_mclp_greedy(self,
                         coverage_matrix: Dict[int, List[int]],
                         demand_weights: List[float],
                         K: int) -> Tuple[List[int], float, Dict]:
        """
        Solve MCLP using greedy heuristic.
        
        This provides a fallback when optimization solvers aren't available.
        """
        print("Using greedy heuristic for MCLP...")
        
        num_demand = len(demand_weights)
        all_sites = set()
        for sites in coverage_matrix.values():
            # Convert site IDs to integers if they're strings
            for site in sites:
                if isinstance(site, str) and site.isdigit():
                    all_sites.add(int(site))
                else:
                    all_sites.add(site)
        all_sites = sorted(list(all_sites))
        
        # Precompute site-to-demand mapping
        site_coverage = {j: [] for j in all_sites}
        for i, covering_sites in coverage_matrix.items():
            for j in covering_sites:
                if j in site_coverage:
                    site_coverage[j].append(i)
                    
        selected_sites = []
        covered_demand = set()
        total_weight = 0
        
        start_time = time.time()
        
        for _ in range(K):
            best_site = None
            best_additional_weight = 0
            
            # Find site that covers most additional weighted demand
            for site in all_sites:
                if site in selected_sites:
                    continue
                    
                # Calculate additional coverage
                additional_demand = set(site_coverage[site]) - covered_demand
                additional_weight = sum(demand_weights[i] for i in additional_demand)
                
                if additional_weight > best_additional_weight:
                    best_additional_weight = additional_weight
                    best_site = site
                    
            if best_site is not None:
                selected_sites.append(best_site)
                covered_demand.update(site_coverage[best_site])
                total_weight += best_additional_weight
            else:
                break  # No more improvements possible
                
        solve_time = time.time() - start_time
        
        solution_info = {
            "status": "greedy_heuristic",
            "objective_value": total_weight,
            "selected_sites": selected_sites,
            "num_sites_selected": len(selected_sites),
            "covered_demand_points": len(covered_demand),
            "total_covered_weight": total_weight,
            "coverage_rate": len(covered_demand) / num_demand,
            "solve_time_sec": solve_time
        }
        
        print(f"Greedy solution: {len(selected_sites)} sites, "
              f"coverage={len(covered_demand)}/{num_demand} ({len(covered_demand)/num_demand:.1%})")
        
        return selected_sites, total_weight, solution_info
        
    def solve_mclp(self,
                  coverage_matrix: Dict[int, List[int]], 
                  demand_weights: List[float],
                  K: int,
                  **kwargs) -> Tuple[List[int], float, Dict]:
        """
        Solve MCLP using the configured solver.
        
        Args:
            coverage_matrix: demand_idx -> list of covering site indices
            demand_weights: Weight for each demand point  
            K: Number of sites to select
            **kwargs: Additional solver-specific options
            
        Returns:
            (selected_sites, objective_value, solution_info)
        """
        if self.solver_type == "ortools" and self.available:
            return self.solve_mclp_ortools(coverage_matrix, demand_weights, K, **kwargs)
        else:
            return self.solve_mclp_greedy(coverage_matrix, demand_weights, K)
            
    def solve_multiple_scenarios(self,
                                coverage_data: Dict,
                                K_values: List[int] = [5, 10, 20],
                                scenarios: List[str] = ["walk", "drive"]) -> Dict:
        """
        Solve MCLP for multiple scenarios.
        
        Args:
            coverage_data: Coverage data for county
            K_values: List of K values to solve
            scenarios: List of scenarios (walk/drive)
            
        Returns:
            Results dictionary
        """
        results = {}
        
        for scenario in scenarios:
            if scenario not in coverage_data:
                print(f"Scenario {scenario} not available")
                continue
                
            print(f"\nSolving scenario: {scenario}")
            scenario_data = coverage_data[scenario]
            
            coverage_matrix = scenario_data["coverage_matrix"]
            demand_weights = scenario_data["demand_metadata"]["demand_weights"]
            
            scenario_results = {}
            
            for K in K_values:
                print(f"  K = {K}")
                
                selected_sites, obj_value, solution_info = self.solve_mclp(
                    coverage_matrix, demand_weights, K
                )
                
                # Add site metadata
                site_metadata = []
                for site_idx in selected_sites:
                    site_info = {
                        "site_index": site_idx,
                        "amenity": scenario_data["supply_metadata"]["amenity_types"][site_idx],
                        "name": scenario_data["supply_metadata"]["site_names"][site_idx],
                        "footprint_area_m2": scenario_data["supply_metadata"]["footprint_areas"][site_idx]
                    }
                    site_metadata.append(site_info)
                    
                solution_info["site_metadata"] = site_metadata
                scenario_results[f"K_{K}"] = solution_info
                
            results[scenario] = scenario_results
            
        return results


def main():
    """Test MCLP solver with sample data."""
    
    # Load coverage data
    coverage_files = [
        "data/int/coverage_Harris_County_TX.json",
        "data/int/coverage_Maricopa_County_AZ.json"
    ]
    
    solver = MCLPSolver()
    
    for coverage_file in coverage_files:
        if not os.path.exists(coverage_file):
            print(f"Coverage file not found: {coverage_file}")
            continue
            
        print(f"\nLoading {coverage_file}...")
        
        with open(coverage_file, 'r') as f:
            coverage_data = json.load(f)
            
        # Solve multiple scenarios
        results = solver.solve_multiple_scenarios(coverage_data)
        
        # Save results
        county_name = coverage_file.split('_')[1:-1]  # Extract county name
        county_name = '_'.join(county_name)
        
        results_file = f"data/out/mclp_results_{county_name}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        print(f"Results saved to {results_file}")


if __name__ == "__main__":
    import os
    main()