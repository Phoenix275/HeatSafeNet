"""Sanity checks on the bundled county coverage data."""


def test_coverage_shape(coverage):
    for scenario in ("walk", "drive"):
        data = coverage[scenario]
        weights = data["demand_metadata"]["demand_weights"]
        n_sites = len(data["supply_metadata"]["site_names"])
        assert len(data["coverage_matrix"]) == len(weights)
        assert all(w >= 0 for w in weights)
        for covering in data["coverage_matrix"].values():
            assert all(0 <= s < n_sites for s in covering)
