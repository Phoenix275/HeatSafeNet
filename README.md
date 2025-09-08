# HeatSafeNet: Optimizing Cooling-&-Connectivity Resilience Hubs for Extreme Heat

[![License](https://img.shields.io/badge/License-Educational%20Use%20Only-red.svg)](#license)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

HeatSafeNet is an open, reproducible geospatial decision-support system that maps neighborhood-level Heat × Digital Exclusion Risk and solves a facility-location optimization to pick the best buildings (libraries/schools/churches/community centers) to serve as Resilience Hubs (cooling + public Wi-Fi + backup power). The system ingests public datasets (NOAA/NASA/CDC/ACS/FCC/OSM), computes a transparent risk index, builds travel-time catchments, solves a Maximal Covering Location Problem (MCLP) with equity and hazard constraints, and ships: (i) a peer-review-style paper, (ii) an interactive web map, (iii) a 2-page policy brief for local officials, and (iv) a fully reproducible GitHub repo and data package.

🌡️ **Problem**: Extreme heat + digital exclusion compound to create vulnerable communities  
🎯 **Solution**: Optimize placement of resilience hubs for maximum equitable coverage  
🔬 **Method**: Multi-criteria risk assessment + integer programming optimization  
🚀 **Impact**: Actionable site recommendations for municipal climate adaptation  

## Quick Start

```bash
# Setup environment
conda env create -f environment.yml
conda activate heatsafenet

# Run full pipeline
make all

# Start interactive web app
make web
# Open browser to http://localhost:8000
```

## Key Features

- **🗺️ Interactive Web App**: Explore risk maps, adjust parameters, and solve optimization in real-time
- **📊 Comprehensive Analysis**: Integrates heat, social vulnerability, digital exclusion, and demographic data
- **⚡ Fast Optimization**: Solves facility location problems in seconds using OR-Tools
- **📈 Publication-Ready Outputs**: Generates figures, tables, and policy briefs automatically
- **🔄 Fully Reproducible**: Complete pipeline from raw data to final recommendations
- **🌍 Open Source**: MIT licensed with extensive documentation

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  Risk Modeling   │───▶│   Optimization  │
│                 │    │                  │    │                 │
│ • NOAA/NASA     │    │ • Heat Exposure  │    │ • MCLP Solver   │
│ • CDC SVI       │    │ • Social Vuln    │    │ • Equity        │
│ • ACS/Census    │    │ • Digital Excl   │    │ • Constraints   │
│ • FCC Broadband │    │ • Demographics   │    │                 │
│ • OpenStreetMap │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   ETL Pipeline  │    │ Network Analysis │    │  Visualization  │
│                 │    │                  │    │                 │
│ • Data fetching │    │ • OSM networks   │    │ • Web interface │
│ • Validation    │    │ • Travel times   │    │ • Static maps   │
│ • Integration   │    │ • Coverage calc  │    │ • Policy briefs │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Demo

![HeatSafeNet Demo](docs/demo.gif)

*Interactive web interface showing risk choropleth, candidate sites, and optimized hub placements for Houston, TX*

## Case Studies

### Houston Metro (Harris County, TX)
- **Coverage**: 78.3% of residents within 10-min walk of optimal hubs
- **Equity**: 82.1% coverage of high-risk populations
- **Sites**: Predominantly schools and libraries in underserved areas

### Phoenix Metro (Maricopa County, AZ)  
- **Coverage**: 71.2% of residents within 10-min walk of optimal hubs
- **Equity**: 79.8% coverage of high-risk populations  
- **Sites**: Mix of community centers and schools in heat-vulnerable zones

## Usage Examples

### Command Line Interface

```bash
# Get help
make help

# Check system status
make status

# Run specific pipeline stages
make data      # Download and process raw data
make features  # Compute risk index components
make network   # Build transportation networks
make solve     # Run optimization scenarios
make figs      # Generate all visualizations

# Quality assurance
make check     # Validate data integrity
make test      # Run unit tests
make lint      # Check code quality
```

### Python API

```python
from heatsafenet import RiskIndexComposer, MCLPSolver
import geopandas as gpd

# Load data
cbg_data = gpd.read_file('data/out/cbg_with_risk_index.geojson')

# Compute risk with custom weights
composer = RiskIndexComposer({
    'heat_exposure': 0.4,
    'social_vulnerability': 0.3,
    'digital_exclusion': 0.2,
    'elderly_vulnerability': 0.1
})

risk_data = composer.compose_risk_index(cbg_data)

# Solve optimization
solver = MCLPSolver()
selected_sites, coverage, info = solver.solve_mclp(
    coverage_matrix, demand_weights, K=10
)

print(f"Selected {len(selected_sites)} sites with {coverage:.1%} coverage")
```

### Web API

```python
import requests

# Get available cities
cities = requests.get('http://localhost:8000/cities').json()

# Solve optimization
response = requests.post('http://localhost:8000/solve', json={
    'city': 'Harris',
    'K': 10, 
    'mode': 'walk',
    'weights': {
        'heat_exposure': 0.35,
        'social_vulnerability': 0.30,
        'digital_exclusion': 0.25,
        'elderly_vulnerability': 0.10
    }
})

results = response.json()
print(f"Coverage rate: {results['summary_stats']['coverage_rate']:.1%}")
```

## Data Sources & Licenses

| Source | Data | License | Usage |
|--------|------|---------|-------|
| **NOAA/NASA** | Heat indices, LST | Public Domain | Heat exposure mapping |
| **CDC** | Social Vulnerability Index | Public Domain | Community vulnerability |
| **U.S. Census** | Demographics, ACS | Public Domain | Population characteristics |
| **FCC** | Broadband availability | Public Domain | Digital inclusion |
| **OpenStreetMap** | Buildings, roads | ODbL | Candidate sites, networks |
| **FEMA** | Flood hazard zones | Public Domain | Site constraints |

All data processing respects source licenses and includes proper attribution.

## Installation

### Requirements

- Python 3.11+
- Conda or Mamba package manager
- ~2GB disk space for full pipeline
- Internet connection for data downloading

### Step-by-Step Setup

1. **Clone repository**:
   ```bash
   git clone https://github.com/your-username/heatsafenet.git
   cd heatsafenet
   ```

2. **Create environment**:
   ```bash
   conda env create -f environment.yml
   conda activate heatsafenet
   ```

3. **Optional API keys** (for enhanced data):
   ```bash
   export CENSUS_API_KEY="your_census_key"  # Faster ACS downloads
   export GOOGLE_EARTH_ENGINE_KEY="path/to/service-account.json"  # GEE LST
   ```

4. **Run pipeline**:
   ```bash
   make all  # Full pipeline (~30 minutes)
   ```

5. **Start web app**:
   ```bash
   make web
   # Open http://localhost:8000
   ```

### Docker Installation

```bash
# Build image
docker build -t heatsafenet .

# Run container
docker run -p 8000:8000 heatsafenet

# Or use docker-compose
docker-compose up
```

## Configuration

### Risk Index Weights

Customize component weights in `src/features/compose_risk.py`:

```python
WEIGHTS = {
    "heat_exposure": 0.35,      # Climate hazard exposure
    "social_vulnerability": 0.30,  # CDC SVI composite
    "digital_exclusion": 0.25,  # Internet access barriers  
    "elderly_vulnerability": 0.10   # Age-based vulnerability
}
```

### Geographic Coverage

Add new study areas in ETL scripts:

```python
COUNTIES = [
    {"state_fips": "48", "county_fips": "201", "name": "Harris County, TX"},
    {"state_fips": "04", "county_fips": "013", "name": "Maricopa County, AZ"},
    {"state_fips": "06", "county_fips": "037", "name": "Los Angeles County, CA"}  # Add new
]
```

### Optimization Parameters

Adjust solver settings in `src/model/mclp_solver.py`:

```python
# Travel time thresholds (minutes)
WALK_TIME = 10
DRIVE_TIME = 10

# Equity constraint (minimum coverage for high-risk areas)
EQUITY_THRESHOLD = 0.6  # 60% minimum coverage

# Site constraints
MIN_BUILDING_SIZE = 300  # square meters
EXCLUDE_FLOOD_ZONES = True
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/your-username/heatsafenet.git
cd heatsafenet
make env
conda activate heatsafenet

# Install development dependencies
pip install -e .
pre-commit install

# Run development checks
make dev-test
```

### Research Collaboration

HeatSafeNet is designed for academic and policy research:

- 📚 **Publications**: Cite our work and consider co-authorship opportunities
- 🔬 **Validation**: Test methods on different geographic areas and datasets  
- 🏛️ **Policy**: Apply results to municipal planning and climate adaptation
- 🛠️ **Extensions**: Add new risk factors, optimization constraints, or visualization features

## Outputs

### For Researchers
- **Paper**: IEEE-format manuscript with methods, results, and validation
- **Figures**: Publication-ready maps, charts, and analysis visualizations  
- **Data**: Processed datasets and reproducible analysis code
- **Benchmarks**: Performance metrics and sensitivity analysis

### For Policymakers
- **Web App**: Interactive tool for exploring scenarios and trade-offs
- **Site Lists**: Ranked recommendations with addresses and justifications
- **Policy Briefs**: 2-page summaries with key findings and next steps
- **Maps**: High-resolution visualizations for presentations and reports

### For Developers
- **Open Source**: Complete codebase under MIT license
- **Documentation**: API reference, tutorials, and implementation guides
- **Tests**: Unit tests and data validation for reliability
- **Docker**: Containerized deployment for cloud and local use

## Citation

If you use HeatSafeNet in your research, please cite:

```bibtex
@software{heatsafenet2024,
  title = {HeatSafeNet: Optimizing Cooling-&-Connectivity Resilience Hubs for Extreme Heat},
  author = {[Your Name] and [Co-Authors]},
  year = {2024},
  url = {https://github.com/your-username/heatsafenet},
  license = {MIT},
  version = {1.0.0}
}
```

## Known Limitations

- **Geographic Scope**: Risk index is normalized within counties; cross-county comparisons require careful interpretation
- **Data Currency**: Demographic and infrastructure data may be 1-2 years behind current conditions
- **Travel Assumptions**: Walking/driving speeds may not reflect local conditions (hills, sidewalk availability)
- **Capacity**: Optimization assumes uniform facility capacity; real buildings vary in size and suitability
- **Dynamic Factors**: Does not account for real-time conditions (weather, traffic, facility availability)

## Roadmap

### Short Term (v1.1)
- [ ] Additional geographic areas (Los Angeles, Miami, Chicago)
- [ ] Enhanced mobile-friendly web interface  
- [ ] Policy brief auto-generation
- [ ] Performance optimizations for large metros

### Medium Term (v2.0)
- [ ] Multi-hazard risk assessment (heat + flooding + power outages)
- [ ] Real-time weather integration
- [ ] Capacity-constrained optimization
- [ ] Multi-objective optimization (coverage + cost + equity)

### Long Term (v3.0)  
- [ ] Machine learning risk prediction
- [ ] Dynamic population modeling
- [ ] Integration with emergency management systems
- [ ] International case studies and data sources

## Support

- **Documentation**: [docs/](docs/) directory and inline code comments
- **Issues**: Report bugs and request features via [GitHub Issues](https://github.com/your-username/heatsafenet/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/your-username/heatsafenet/discussions)
- **Email**: Contact maintainers for urgent matters or partnership inquiries

## Acknowledgments

HeatSafeNet builds on excellent open-source tools and data sources:

- **Geospatial**: GeoPandas, Shapely, Contextily, OSMnx
- **Optimization**: OR-Tools, PuLP  
- **Web**: FastAPI, Leaflet, Folium
- **Analysis**: Pandas, NumPy, Scikit-learn
- **Visualization**: Matplotlib, Seaborn

Special thanks to:
- OpenStreetMap community for infrastructure data
- U.S. Census Bureau for demographic data access
- NOAA and NASA for climate datasets
- Academic collaborators and municipal partners

## License

Educational Use License - see [LICENSE](LICENSE) file for details. 

**⚠️ Important**: This project is licensed for educational and demonstration purposes only. Commercial use requires explicit permission.

**Climate change demands urgent action. HeatSafeNet provides the tools—use them to build resilient communities.** 🌡️➡️❄️