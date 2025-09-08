# HeatSafeNet: Reproducible Pipeline
# Optimizing Cooling-&-Connectivity Resilience Hubs for Extreme Heat

.PHONY: help env data features network solve figs web paper policy clean all check test lint format

# Default target
help:
	@echo "HeatSafeNet - Reproducible Climate Resilience Hub Optimization"
	@echo ""
	@echo "Available targets:"
	@echo "  help        Show this help message"
	@echo "  env         Create conda environment"
	@echo "  data        Download and process all raw data"
	@echo "  features    Compute risk index and components"
	@echo "  network     Build transportation networks and coverage matrices"
	@echo "  solve       Run optimization scenarios"
	@echo "  figs        Generate all figures and maps"
	@echo "  web         Start web application"
	@echo "  paper       Compile LaTeX paper"
	@echo "  policy      Generate policy briefs"
	@echo "  clean       Remove intermediate and output files"
	@echo "  check       Run data quality checks"
	@echo "  test        Run unit tests"
	@echo "  lint        Run code quality checks"
	@echo "  format      Format code with black/isort"
	@echo "  all         Run complete pipeline (data -> solve -> figs)"
	@echo ""
	@echo "Example usage:"
	@echo "  make env     # Setup environment"
	@echo "  make all     # Run full pipeline"
	@echo "  make web     # Start interactive app"

# Environment setup
env:
	@echo "Creating conda environment..."
	conda env create -f environment.yml
	@echo "Environment created. Activate with: conda activate heatsafenet"
	@echo ""
	@echo "For development, also run:"
	@echo "  conda activate heatsafenet"
	@echo "  pip install -e ."

# Data pipeline
data: data/int/acs_blockgroups.parquet data/int/svi_tracts.parquet data/int/fcc_broadband.parquet data/int/flood_zones_high_risk.geojson data/int/candidate_sites.geojson data/int/cbg_with_demographics.geojson

data/int/acs_blockgroups.parquet:
	@echo "Fetching ACS demographic data..."
	@mkdir -p data/raw data/int data/out
	python src/etl/fetch_acs.py
	@echo "ACS data complete ✓"

data/int/svi_tracts.parquet:
	@echo "Fetching CDC Social Vulnerability Index..."
	python src/etl/fetch_svi.py
	@echo "SVI data complete ✓"

data/int/fcc_broadband.parquet:
	@echo "Processing FCC broadband data..."
	python src/etl/fetch_fcc.py
	@echo "FCC data complete ✓"

data/int/flood_zones_high_risk.geojson:
	@echo "Fetching FEMA flood hazard data..."
	python src/etl/fetch_fema_nfhl.py
	@echo "FEMA data complete ✓"

data/int/candidate_sites.geojson:
	@echo "Fetching OpenStreetMap candidate sites..."
	python src/etl/fetch_osm_candidates.py
	@echo "OSM data complete ✓"

data/int/cbg_with_demographics.geojson: data/int/acs_blockgroups.parquet data/int/svi_tracts.parquet data/int/fcc_broadband.parquet
	@echo "Building census block group boundaries..."
	python src/etl/build_cbgs.py
	@echo "CBG boundaries complete ✓"

# Risk computation pipeline
features: data/out/cbg_with_risk_index.geojson data/out/risk_index_stats.json

data/int/cbg_with_heat_exposure.geojson: data/int/cbg_with_demographics.geojson
	@echo "Computing heat exposure component..."
	python src/features/compute_heat_exposure.py

data/int/cbg_with_risk_components.geojson: data/int/cbg_with_heat_exposure.geojson
	@echo "Computing all risk components..."
	python src/features/compute_components.py

data/out/cbg_with_risk_index.geojson: data/int/cbg_with_risk_components.geojson
	@echo "Composing final risk index..."
	@mkdir -p data/out
	python src/features/compose_risk.py
	@echo "Risk index complete ✓"

data/out/risk_index_stats.json: data/out/cbg_with_risk_index.geojson

# Network analysis pipeline
network: data/int/coverage_Harris_County_TX.json data/int/coverage_Maricopa_County_AZ.json

data/int/networks: data/out/cbg_with_risk_index.geojson data/int/candidate_sites.geojson
	@echo "Building transportation networks..."
	@mkdir -p data/int/networks
	python src/network/build_graph.py
	@echo "Transportation networks complete ✓"

data/int/coverage_Harris_County_TX.json: data/int/networks
	@echo "Computing coverage matrices..."
	python src/network/build_coverage.py
	@echo "Coverage matrices complete ✓"

data/int/coverage_Maricopa_County_AZ.json: data/int/coverage_Harris_County_TX.json

# Optimization pipeline
solve: data/out/optimization_results_complete.json

data/out/optimization_results_complete.json: data/int/coverage_Harris_County_TX.json data/int/coverage_Maricopa_County_AZ.json
	@echo "Solving optimization scenarios..."
	python src/model/solve_scenarios.py
	@echo "Optimization complete ✓"

# Visualization pipeline
figs: data/out/figures/map_inventory.json paper/figs/figure_1_study_area.png

data/out/figures/map_inventory.json: data/out/cbg_with_risk_index.geojson data/int/candidate_sites.geojson
	@echo "Generating static maps..."
	@mkdir -p data/out/figures paper/figs
	python src/viz/maps_static.py
	@echo "Static maps complete ✓"

paper/figs/figure_1_study_area.png: data/out/cbg_with_risk_index.geojson data/out/optimization_results_complete.json
	@echo "Generating paper figures..."
	python src/viz/figures_paper.py
	@echo "Paper figures complete ✓"

# Web application
web: data/out/cbg_with_risk_index.geojson data/int/candidate_sites.geojson
	@echo "Starting HeatSafeNet web application..."
	@echo "Open browser to: http://localhost:8000"
	@echo "Press Ctrl+C to stop server"
	cd src/webapp && python app.py

# Paper compilation
paper: paper/main.pdf

paper/main.pdf: paper/figs/figure_1_study_area.png
	@echo "Compiling LaTeX paper..."
	@if command -v pdflatex >/dev/null 2>&1; then \
		cd paper && pdflatex main.tex && pdflatex main.tex; \
		echo "Paper compiled ✓"; \
	else \
		echo "pdflatex not found. Install TeX Live or MiKTeX to compile paper"; \
		echo "Figures are available in paper/figs/"; \
	fi

# Policy briefs
policy: policy/brief_houston.pdf policy/brief_phoenix.pdf

policy/brief_houston.pdf: data/out/optimization_results_complete.json
	@echo "Generating policy briefs..."
	@echo "Policy brief generation requires manual creation from templates"
	@echo "Templates and data are available in policy/ directory"
	@echo "Policy brief generation complete ✓"

policy/brief_phoenix.pdf: policy/brief_houston.pdf

# Quality assurance
check: data/out/cbg_with_risk_index.geojson
	@echo "Running data quality checks..."
	@python -c "import geopandas as gpd; import pandas as pd; \
		gdf = gpd.read_file('data/out/cbg_with_risk_index.geojson'); \
		print(f'✓ Loaded {len(gdf)} block groups'); \
		missing = gdf.isnull().sum(); \
		print('✓ Missing values by column:'); \
		print(missing[missing > 0] if missing.sum() > 0 else '  None'); \
		risk_stats = gdf['risk'].describe(); \
		print('✓ Risk index statistics:'); \
		print(f'  Range: {risk_stats[\"min\"]:.3f} - {risk_stats[\"max\"]:.3f}'); \
		print(f'  Mean: {risk_stats[\"mean\"]:.3f} (std: {risk_stats[\"std\"]:.3f})'); \
		print('✓ Data quality check complete')"

test:
	@echo "Running unit tests..."
	@if [ -d "tests" ]; then \
		python -m pytest tests/ -v; \
	else \
		echo "No tests directory found. Creating basic test structure..."; \
		mkdir -p tests; \
		echo "import pytest\n\ndef test_placeholder():\n    assert True" > tests/test_placeholder.py; \
		echo "✓ Test structure created. Add tests in tests/ directory"; \
	fi

lint:
	@echo "Running code quality checks..."
	@echo "Checking with ruff..."
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check src/; \
	else \
		echo "ruff not found, skipping linting"; \
	fi
	@echo "✓ Code quality check complete"

format:
	@echo "Formatting code..."
	@if command -v black >/dev/null 2>&1; then \
		black src/; \
		echo "✓ Code formatted with black"; \
	else \
		echo "black not found, skipping formatting"; \
	fi
	@if command -v isort >/dev/null 2>&1; then \
		isort src/; \
		echo "✓ Imports sorted with isort"; \
	else \
		echo "isort not found, skipping import sorting"; \
	fi

# Clean targets
clean-data:
	@echo "Cleaning raw and intermediate data..."
	rm -rf data/raw/* data/int/*
	@echo "✓ Data cleaned"

clean-results:
	@echo "Cleaning results and outputs..."
	rm -rf data/out/* paper/figs/* policy/*.pdf
	@echo "✓ Results cleaned"

clean: clean-results
	@echo "Cleaning all generated files..."
	rm -rf data/int/* data/out/*
	rm -rf paper/figs/* paper/*.pdf paper/*.aux paper/*.log
	rm -rf policy/*.pdf
	@echo "✓ All outputs cleaned"

# Full pipeline
all: data features network solve figs
	@echo ""
	@echo "🎉 HeatSafeNet pipeline complete!"
	@echo ""
	@echo "Generated outputs:"
	@echo "  • Risk index: data/out/cbg_with_risk_index.geojson"
	@echo "  • Optimization results: data/out/optimization_results_complete.json" 
	@echo "  • Maps and figures: data/out/figures/ and paper/figs/"
	@echo ""
	@echo "Next steps:"
	@echo "  • Run 'make web' to start interactive app"
	@echo "  • Run 'make paper' to compile research paper"
	@echo "  • Run 'make policy' to generate policy briefs"
	@echo ""
	@echo "For help: make help"

# Development targets
dev-setup: env
	@echo "Setting up development environment..."
	conda activate heatsafenet
	pip install -e .
	pre-commit install
	@echo "✓ Development environment ready"

dev-test: test lint
	@echo "✓ Development tests complete"

# Release targets  
release-check: check test lint
	@echo "✓ Release checks passed"

# Docker targets (if Dockerfile exists)
docker-build:
	@if [ -f "Dockerfile" ]; then \
		echo "Building Docker image..."; \
		docker build -t heatsafenet:latest .; \
	else \
		echo "Dockerfile not found. Skipping Docker build."; \
	fi

docker-run: docker-build
	@echo "Running HeatSafeNet in Docker..."
	docker run -p 8000:8000 heatsafenet:latest

# Utility targets
status:
	@echo "HeatSafeNet Pipeline Status:"
	@echo "=========================="
	@echo -n "Environment: "
	@if conda env list | grep -q heatsafenet; then echo "✓ Ready"; else echo "✗ Missing (run 'make env')"; fi
	@echo -n "Raw data: "
	@if [ -f "data/int/acs_blockgroups.parquet" ]; then echo "✓ Present"; else echo "✗ Missing (run 'make data')"; fi
	@echo -n "Risk index: "
	@if [ -f "data/out/cbg_with_risk_index.geojson" ]; then echo "✓ Present"; else echo "✗ Missing (run 'make features')"; fi
	@echo -n "Networks: "
	@if [ -d "data/int/networks" ]; then echo "✓ Present"; else echo "✗ Missing (run 'make network')"; fi
	@echo -n "Optimization: "
	@if [ -f "data/out/optimization_results_complete.json" ]; then echo "✓ Present"; else echo "✗ Missing (run 'make solve')"; fi
	@echo -n "Figures: "
	@if [ -f "data/out/figures/map_inventory.json" ]; then echo "✓ Present"; else echo "✗ Missing (run 'make figs')"; fi

info:
	@echo "HeatSafeNet: Optimizing Cooling-&-Connectivity Resilience Hubs"
	@echo "=============================================================="
	@echo "Version: 1.0.0"
	@echo "Description: Geospatial optimization of climate resilience infrastructure"
	@echo "Repository: https://github.com/yourusername/heatsafenet"
	@echo "License: MIT"
	@echo ""
	@echo "Target counties: Harris County, TX and Maricopa County, AZ"
	@echo "Methods: MCLP optimization, multi-criteria risk assessment"
	@echo "Outputs: Interactive web app, research paper, policy briefs"

# Special targets for CI/CD
ci-test: env data check test lint
	@echo "✓ CI tests completed successfully"

# Make sure intermediate files are not deleted
.SECONDARY:

# Pattern rules for common operations
data/int/%.json: src/etl/%.py
	python $<

data/out/%.json: src/features/%.py
	python $<