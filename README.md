# HeatSafeNet: Climate Resilience Optimization System

[![License](https://img.shields.io/badge/License-Educational%20Use%20Only-red.svg)](#license)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

HeatSafeNet is a geospatial decision-support system that optimizes cooling center placement for extreme heat events. The system combines heat exposure data, social vulnerability indicators, and digital exclusion metrics to solve facility location problems using advanced optimization algorithms. It features an interactive web interface for real-time scenario analysis and planning.

🌡️ **Problem**: Extreme heat + digital exclusion compound to create vulnerable communities  
🎯 **Solution**: Optimize placement of resilience hubs for maximum equitable coverage  
🔬 **Method**: Multi-criteria risk assessment + integer programming optimization  
🚀 **Impact**: Actionable site recommendations for municipal climate adaptation  

## Quick Start

```bash
# Setup environment
python -m venv heatsafenet-env
source heatsafenet-env/bin/activate  # On Windows: heatsafenet-env\Scripts\activate
pip install -r requirements.txt

# Run the application
python src/webapp/app.py
# Open browser to http://localhost:8000
```

## Key Features

- **🗺️ Interactive Web App**: Explore risk maps, adjust parameters, and solve optimization in real-time
- **📊 Multi-Criteria Analysis**: Integrates heat, social vulnerability, digital exclusion, and demographic data
- **⚡ Fast Optimization**: Solves facility location problems in seconds using OR-Tools
- **🔄 Fully Functional**: Complete pipeline from data processing to optimization results
- **🌍 Open Source**: Educational use with comprehensive documentation

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  Risk Modeling   │───▶│   Optimization  │
│                 │    │                  │    │                 │
│ • Census Data   │    │ • Heat Exposure  │    │ • MCLP Solver   │
│ • Climate Data  │    │ • Social Vuln    │    │ • Coverage Max  │
│ • OpenStreetMap │    │ • Digital Excl   │    │ • Constraints   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   ETL Pipeline  │    │ Network Analysis │    │  Web Interface  │
│                 │    │                  │    │                 │
│ • Data fetching │    │ • Travel times   │    │ • Leaflet maps  │
│ • Validation    │    │ • Coverage calc  │    │ • Real-time UI  │
│ • Integration   │    │ • Accessibility  │    │ • Controls      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Demo Results

### Houston Metro (Harris County, TX)
- **Coverage**: 87% of residents within 10-min walk of optimal hubs
- **Efficiency**: 5 facilities selected from 20 candidates
- **Performance**: Optimal solution found in <2 seconds

### Phoenix Metro (Maricopa County, AZ)  
- **Coverage**: 85% of residents within 10-min walk of optimal hubs
- **Efficiency**: 5 facilities selected from 20 candidates  
- **Performance**: Optimal solution found in <2 seconds

## Tests and Benchmarks

```bash
pip install -r requirements-dev.txt
pytest -q                          # solver correctness, including brute-force checks
python benchmarks/bench_mclp.py    # exact (OR-Tools) vs greedy: time and optimality gap
```

GitHub Actions runs both on every push. On the bundled data and larger random instances, the greedy heuristic reaches 98 to 100% of the optimal coverage objective in a few milliseconds. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the model, full results, and a note on the demo data.

## Technical Implementation

### Technologies Used
- **Backend**: Python, FastAPI, OR-Tools optimization
- **Frontend**: JavaScript, Leaflet mapping, responsive UI
- **Data Processing**: GeoPandas, NetworkX, Pandas
- **APIs**: Census API, Google Earth Engine (optional)

### Key Algorithms
- **Optimization**: Maximum Covering Location Problem (MCLP)
- **Risk Assessment**: Multi-criteria weighted scoring
- **Network Analysis**: Travel-time based accessibility
- **Spatial Analysis**: GIS operations and geometric processing

## Installation

### Requirements
- Python 3.11+
- ~500MB disk space
- Internet connection for data access

### Setup Steps

1. **Clone repository**:
   ```bash
   git clone https://github.com/Phoenix275/HeatSafeNet.git
   cd HeatSafeNet
   ```

2. **Create environment**:
   ```bash
   python -m venv heatsafenet-env
   source heatsafenet-env/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Optional API keys** (for enhanced data):
   ```bash
   # Copy and edit with your keys
   cp .env.example .env
   ```

5. **Run application**:
   ```bash
   python src/webapp/app.py
   # Open http://localhost:8000
   ```

## Usage

### Web Interface
1. **Select County**: Choose Harris County, TX or Maricopa County, AZ
2. **Adjust Risk Weights**: Use sliders to set importance of different risk factors
3. **Set Parameters**: Choose number of facilities and travel mode
4. **Run Optimization**: Click "Solve" to find optimal locations
5. **View Results**: Explore coverage maps and facility recommendations

### API Endpoints
```python
import requests

# Get available cities
cities = requests.get('http://localhost:8000/cities').json()

# Run optimization
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
print(f"Coverage: {results['summary_stats']['coverage_rate']:.1%}")
```

## Project Structure

```
HeatSafeNet/
├── src/
│   ├── etl/              # Data extraction and processing
│   ├── model/            # Optimization algorithms
│   ├── features/         # Risk computation
│   ├── network/          # Travel-time analysis
│   ├── viz/              # Visualization tools
│   └── webapp/           # Web application
├── data/                 # Data storage (gitignored)
├── requirements.txt      # Python dependencies
├── .env.example         # API key template
└── README.md           # This file
```

## Data Sources

| Source | Data Type | Usage |
|--------|-----------|-------|
| **U.S. Census** | Demographics, ACS | Population characteristics |
| **CDC** | Social Vulnerability Index | Community vulnerability |
| **OpenStreetMap** | Buildings, roads | Candidate sites, networks |
| **Google Earth Engine** | Satellite temperature | Heat exposure (optional) |

All data processing respects source licenses and includes proper attribution.

## Performance

- **Optimization Speed**: <2 seconds for typical problems
- **Coverage Quality**: 85-90% population coverage achieved
- **Scalability**: Handles 100+ demand points, 20+ candidate sites
- **Memory Usage**: <1GB RAM for standard county analysis

## License

Educational Use License - see [LICENSE](LICENSE) file for details.

**⚠️ Important**: This project is licensed for educational and demonstration purposes only. Commercial use requires explicit permission.

---

*Advanced geospatial optimization system demonstrating expertise in Python, JavaScript, operations research, and full-stack development.*