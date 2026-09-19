"""Correctness tests for the MCLP solver (OR-Tools and greedy)."""

import itertools
import random

import pytest

from mclp_solver import MCLPSolver


def brute_force(coverage, weights, k):
    sites = sorted({s for covering in coverage.values() for s in covering})
    best = 0.0
    for combo in itertools.combinations(sites, min(k, len(sites))):
        chosen = set(combo)
        value = sum(w for i, w in enumerate(weights) if chosen & set(coverage.get(i, [])))
        best = max(best, value)
    return best


def random_instance(seed, n_demand=30, n_sites=10):
    rng = random.Random(seed)
    coverage = {i: rng.sample(range(n_sites), rng.randint(1, 3)) for i in range(n_demand)}
    weights = [round(rng.uniform(0.1, 1.0), 3) for _ in range(n_demand)]
    return coverage, weights


@pytest.fixture(scope="module")
def ortools_solver():
    solver = MCLPSolver("ortools")
    if solver.solver_type != "ortools":
        pytest.skip("OR-Tools not installed")
    return solver


@pytest.mark.parametrize("seed", range(5))
def test_ortools_matches_brute_force(ortools_solver, seed):
    coverage, weights = random_instance(seed)
    _, value, info = ortools_solver.solve_mclp(coverage, weights, K=3)
    assert info["status"] == "optimal"
    assert value == pytest.approx(brute_force(coverage, weights, 3), abs=1e-6)


@pytest.mark.parametrize("seed", range(5))
def test_greedy_is_feasible_and_near_optimal(ortools_solver, seed):
    coverage, weights = random_instance(seed)
    sites, greedy_value, _ = MCLPSolver("ortools").solve_mclp_greedy(coverage, weights, K=3)
    _, optimal_value, _ = ortools_solver.solve_mclp(coverage, weights, K=3)
    assert len(sites) <= 3
    assert len(set(sites)) == len(sites)
    assert greedy_value <= optimal_value + 1e-9
    # Greedy max coverage is guaranteed at least (1 - 1/e) of optimal.
    assert greedy_value >= (1 - 1 / 2.718281828) * optimal_value - 1e-9


def test_budget_is_respected(ortools_solver):
    coverage, weights = random_instance(42, n_demand=50, n_sites=15)
    for k in (1, 2, 5):
        sites, _, info = ortools_solver.solve_mclp(coverage, weights, K=k)
        assert len(sites) <= k
        assert info["num_sites_selected"] == len(sites)


def test_more_sites_never_covers_less(ortools_solver):
    coverage, weights = random_instance(7, n_demand=40, n_sites=12)
    values = [ortools_solver.solve_mclp(coverage, weights, K=k)[1] for k in (1, 2, 3, 4, 5)]
    assert values == sorted(values)


def test_greedy_handles_string_keys_from_json():
    # json.load turns int keys into strings; the solver must accept both.
    coverage = {"0": [0], "1": [0, 1], "2": [1]}
    weights = [1.0, 2.0, 3.0]
    sites, value, info = MCLPSolver("ortools").solve_mclp_greedy(coverage, weights, K=1)
    assert sites == [1]
    assert value == pytest.approx(5.0)
    assert info["covered_demand_points"] == 2


def test_equity_constraint_covers_high_risk_demand(ortools_solver):
    coverage, weights = random_instance(3, n_demand=40, n_sites=12)
    _, _, info = ortools_solver.solve_mclp(
        coverage, weights, K=2, equity_constraint=True, equity_threshold=0.5
    )
    assert info["status"] in {"optimal", "infeasible_or_unbounded"}


@pytest.mark.parametrize("scenario", ["walk", "drive"])
def test_real_county_coverage_solves(ortools_solver, coverage, scenario):
    data = coverage[scenario]
    weights = data["demand_metadata"]["demand_weights"]
    sites, value, info = ortools_solver.solve_mclp(data["coverage_matrix"], weights, K=5)
    assert info["status"] == "optimal"
    assert 0 < len(sites) <= 5
    assert 0 < value <= sum(weights) + 1e-9
    _, greedy_value, _ = ortools_solver.solve_mclp_greedy(data["coverage_matrix"], weights, K=5)
    assert greedy_value <= value + 1e-9
