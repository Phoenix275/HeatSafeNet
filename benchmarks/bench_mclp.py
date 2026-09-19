"""Benchmark the MCLP solver: OR-Tools (exact) vs the greedy heuristic.

Reports solve time and how close greedy gets to the optimum, on the bundled
county coverage data and on larger random instances.

    python benchmarks/bench_mclp.py
"""

import contextlib
import importlib
import io
import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "model"))

# Loaded after the path tweak above; importlib keeps linters happy across ruff versions.
MCLPSolver = importlib.import_module("mclp_solver").MCLPSolver


def quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def random_instance(seed, n_demand, n_sites):
    rng = random.Random(seed)
    coverage = {i: rng.sample(range(n_sites), rng.randint(1, 6)) for i in range(n_demand)}
    weights = [rng.uniform(0.1, 1.0) for _ in range(n_demand)]
    return coverage, weights


def run(label, coverage, weights, k, solver):
    t0 = time.perf_counter()
    _, opt_value, info = quiet(solver.solve_mclp, coverage, weights, k)
    opt_time = time.perf_counter() - t0
    t0 = time.perf_counter()
    _, greedy_value, _ = quiet(solver.solve_mclp_greedy, coverage, weights, k)
    greedy_time = time.perf_counter() - t0
    ratio = greedy_value / opt_value if opt_value else 1.0
    covered = info.get("coverage_rate", 0.0)
    print(f"{label:<34} K={k:<3} exact {1000 * opt_time:7.1f} ms  greedy {1000 * greedy_time:6.1f} ms  "
          f"greedy/optimal {ratio:.3f}  demand covered {covered:.0%}")
    return ratio, opt_time


def main():
    solver = quiet(MCLPSolver, "ortools")
    if solver.solver_type != "ortools":
        sys.exit("OR-Tools is required for this benchmark")

    ratios = []
    for path in sorted((ROOT / "data" / "int").glob("coverage_*.json")):
        data = json.loads(path.read_text())
        county = path.stem.replace("coverage_", "").replace("_", " ")
        for scenario in ("walk", "drive"):
            d = data[scenario]
            for k in (3, 5, 10):
                r, _ = run(f"{county} ({scenario})", d["coverage_matrix"], d["demand_metadata"]["demand_weights"], k, solver)
                ratios.append(r)

    for n_demand, n_sites in ((300, 40), (600, 60)):
        coverage, weights = random_instance(0, n_demand, n_sites)
        r, _ = run(f"random {n_demand} demand / {n_sites} sites", coverage, weights, 10, solver)
        ratios.append(r)

    print(f"\ngreedy reaches on average {statistics.mean(ratios):.1%} of the optimal objective "
          f"(worst case {min(ratios):.1%})")


if __name__ == "__main__":
    main()
