// HeatSafeNet Frontend JavaScript

// Global variables
let map;
let currentCity = null;
let riskLayer = null;
let candidateLayer = null;
let selectedSitesLayer = null;

// API Base URL
const API_BASE = window.location.origin;

// Color schemes
const RISK_COLORS = {
    0: '#ffffcc', // Low (0.0-0.2)
    1: '#a1dab4', // Low-Med (0.2-0.4)
    2: '#41b6c4', // Medium (0.4-0.6)
    3: '#2c7fb8', // Med-High (0.6-0.8)
    4: '#253494'  // High (0.8-1.0)
};

const AMENITY_ICONS = {
    'school': '🏫',
    'library': '📚', 
    'community_centre': '🏛️',
    'place_of_worship': '⛪',
    'hospital': '🏥'
};

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeMap();
    loadAvailableCities();
    setupEventListeners();
    updateWeightDisplays();
});

function initializeMap() {
    // Initialize Leaflet map
    map = L.map('map').setView([29.8, -95.4], 10); // Default to Houston
    
    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Initialize layer groups
    riskLayer = L.layerGroup().addTo(map);
    candidateLayer = L.layerGroup().addTo(map);
    selectedSitesLayer = L.layerGroup().addTo(map);
}

function setupEventListeners() {
    // City selection
    document.getElementById('citySelect').addEventListener('change', function() {
        const city = this.value;
        if (city) {
            loadCityData(city);
        }
    });
    
    // Weight sliders
    const weightSliders = ['heatWeight', 'socialWeight', 'digitalWeight', 'elderlyWeight'];
    weightSliders.forEach(sliderId => {
        document.getElementById(sliderId).addEventListener('input', updateWeights);
    });
    
    // K value slider
    document.getElementById('kSlider').addEventListener('input', function() {
        document.getElementById('kValue').textContent = this.value;
    });
    
    // Solve button
    document.getElementById('solveButton').addEventListener('click', solveOptimization);
}

async function loadAvailableCities() {
    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/cities`);
        const data = await response.json();
        
        const citySelect = document.getElementById('citySelect');
        citySelect.innerHTML = '<option value="">Select a city...</option>';
        
        data.cities.forEach(city => {
            const option = document.createElement('option');
            option.value = city.key;
            option.textContent = city.name;
            citySelect.appendChild(option);
        });
        
    } catch (error) {
        showMessage('Error loading cities: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function loadCityData(cityKey) {
    try {
        showLoading(true);
        currentCity = cityKey;
        
        // Load risk data
        const riskResponse = await fetch(`${API_BASE}/risk/${cityKey}`);
        const riskData = await riskResponse.json();
        
        // Load candidate sites
        const candidatesResponse = await fetch(`${API_BASE}/candidates/${cityKey}`);
        const candidatesData = await candidatesResponse.json();
        
        // Display data on map
        displayRiskData(riskData);
        displayCandidateSites(candidatesData);
        
        // Fit map to city bounds
        const bounds = L.geoJSON(riskData).getBounds();
        map.fitBounds(bounds);
        
        // Load city statistics
        loadCityStats(cityKey);
        
    } catch (error) {
        showMessage('Error loading city data: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function displayRiskData(geoJsonData) {
    // Clear existing risk layer
    riskLayer.clearLayers();
    
    const riskGeoJson = L.geoJSON(geoJsonData, {
        style: function(feature) {
            const risk = feature.properties.risk || 0;
            const colorIndex = getRiskColorIndex(risk);
            
            return {
                fillColor: RISK_COLORS[colorIndex],
                weight: 0.5,
                opacity: 1,
                color: 'white',
                fillOpacity: 0.7
            };
        },
        onEachFeature: function(feature, layer) {
            // Create popup with risk information
            const props = feature.properties;
            const popupContent = `
                <div style="font-size: 12px;">
                    <strong>Block Group:</strong> ${props.GEOID || 'Unknown'}<br>
                    <strong>Risk Score:</strong> ${(props.risk || 0).toFixed(3)}<br>
                    <strong>Population:</strong> ${props.total_population || 'N/A'}<br>
                    <strong>Heat Exposure:</strong> ${(props.heat_exposure || 0).toFixed(3)}<br>
                    <strong>Social Vuln:</strong> ${(props.social_vulnerability || 0).toFixed(3)}<br>
                    <strong>Digital Exclusion:</strong> ${(props.digital_exclusion || 0).toFixed(3)}<br>
                    <strong>Elderly Share:</strong> ${(props.elderly_vulnerability || 0).toFixed(3)}
                </div>
            `;
            layer.bindPopup(popupContent);
        }
    });
    
    riskGeoJson.addTo(riskLayer);
}

function displayCandidateSites(geoJsonData) {
    // Clear existing candidate layer
    candidateLayer.clearLayers();
    
    const candidateGeoJson = L.geoJSON(geoJsonData, {
        pointToLayer: function(feature, latlng) {
            const amenity = feature.properties.amenity || 'unknown';
            const icon = AMENITY_ICONS[amenity] || '📍';
            
            return L.marker(latlng, {
                icon: L.divIcon({
                    html: `<div style="font-size: 16px; text-align: center;">${icon}</div>`,
                    className: 'candidate-icon',
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                })
            });
        },
        onEachFeature: function(feature, layer) {
            const props = feature.properties;
            const popupContent = `
                <div style="font-size: 12px;">
                    <strong>${props.name || 'Unnamed'}</strong><br>
                    <strong>Type:</strong> ${props.amenity || 'Unknown'}<br>
                    <strong>Address:</strong> ${props.addr_street || ''}<br>
                    <strong>Size:</strong> ${(props.footprint_area_m2 || 0).toFixed(0)} m²
                </div>
            `;
            layer.bindPopup(popupContent);
        }
    });
    
    candidateGeoJson.addTo(candidateLayer);
}

function getRiskColorIndex(risk) {
    if (risk < 0.2) return 0;
    if (risk < 0.4) return 1;
    if (risk < 0.6) return 2;
    if (risk < 0.8) return 3;
    return 4;
}

function updateWeights() {
    // Get current values
    const heat = parseInt(document.getElementById('heatWeight').value);
    const social = parseInt(document.getElementById('socialWeight').value);
    const digital = parseInt(document.getElementById('digitalWeight').value);
    const elderly = parseInt(document.getElementById('elderlyWeight').value);
    
    const total = heat + social + digital + elderly;
    
    // Update displays
    document.getElementById('heatWeightValue').textContent = heat + '%';
    document.getElementById('socialWeightValue').textContent = social + '%';
    document.getElementById('digitalWeightValue').textContent = digital + '%';
    document.getElementById('elderlyWeightValue').textContent = elderly + '%';
    document.getElementById('totalWeight').textContent = total + '%';
    
    // Color code total based on validity
    const totalElement = document.getElementById('totalWeight');
    if (total === 100) {
        totalElement.style.color = '#28a745';
    } else {
        totalElement.style.color = '#dc3545';
    }
    
    // Enable/disable solve button
    const solveButton = document.getElementById('solveButton');
    solveButton.disabled = total !== 100 || !currentCity;
}

function updateWeightDisplays() {
    updateWeights();
}

async function solveOptimization() {
    if (!currentCity) {
        showMessage('Please select a city first', 'error');
        return;
    }
    
    // Get parameters
    const K = parseInt(document.getElementById('kSlider').value);
    const mode = document.getElementById('modeSelect').value;
    
    const weights = {
        heat_exposure: parseInt(document.getElementById('heatWeight').value) / 100,
        social_vulnerability: parseInt(document.getElementById('socialWeight').value) / 100,
        digital_exclusion: parseInt(document.getElementById('digitalWeight').value) / 100,
        elderly_vulnerability: parseInt(document.getElementById('elderlyWeight').value) / 100
    };
    
    // Validate weights sum to 1
    const weightSum = Object.values(weights).reduce((a, b) => a + b, 0);
    if (Math.abs(weightSum - 1.0) > 0.001) {
        showMessage('Weights must sum to 100%', 'error');
        return;
    }
    
    try {
        showLoading(true);
        document.getElementById('solveButton').disabled = true;
        
        const response = await fetch(`${API_BASE}/solve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                city: currentCity,
                K: K,
                mode: mode,
                weights: weights
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Optimization failed');
        }
        
        const result = await response.json();
        displayOptimizationResults(result);
        
    } catch (error) {
        showMessage('Optimization error: ' + error.message, 'error');
    } finally {
        showLoading(false);
        document.getElementById('solveButton').disabled = false;
    }
}

function displayOptimizationResults(result) {
    // Clear existing selected sites
    selectedSitesLayer.clearLayers();
    
    // Display selected sites on map
    result.selected_sites.forEach((site, index) => {
        if (site.coordinates && site.coordinates.lat && site.coordinates.lon) {
            const marker = L.marker([site.coordinates.lat, site.coordinates.lon], {
                icon: L.divIcon({
                    html: `<div style="
                        background: #e74c3c;
                        color: white;
                        border-radius: 50%;
                        width: 24px;
                        height: 24px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-weight: bold;
                        font-size: 12px;
                        border: 2px solid white;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                    ">${index + 1}</div>`,
                    className: 'selected-site-icon',
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                })
            });
            
            const popupContent = `
                <div style="font-size: 12px;">
                    <strong>Selected Hub #${index + 1}</strong><br>
                    <strong>Name:</strong> ${site.name}<br>
                    <strong>Type:</strong> ${site.amenity}<br>
                    <strong>Coverage:</strong> ${site.catchment_stats.covered_population || 0} people
                </div>
            `;
            marker.bindPopup(popupContent);
            
            selectedSitesLayer.addLayer(marker);
        }
    });
    
    // Update results panel
    const stats = result.summary_stats;
    document.getElementById('sitesSelected').textContent = stats.sites_selected;
    document.getElementById('coverageRate').textContent = (stats.coverage_rate * 100).toFixed(1) + '%';
    document.getElementById('coveredPopulation').textContent = stats.covered_demand_points.toLocaleString();
    document.getElementById('solveTime').textContent = parseFloat(result.solution_metadata.solve_time_sec).toFixed(2) + 's';
    
    // Show results section
    document.getElementById('resultsSection').style.display = 'block';
    
    // Show success message
    showMessage(`Optimization complete! Selected ${stats.sites_selected} sites with ${(stats.coverage_rate * 100).toFixed(1)}% coverage.`, 'success');
}

async function loadCityStats(cityKey) {
    try {
        const response = await fetch(`${API_BASE}/stats/${cityKey}`);
        const stats = await response.json();
        
        console.log('City stats loaded:', stats);
        // Could display additional statistics in UI if needed
        
    } catch (error) {
        console.warn('Could not load city statistics:', error);
    }
}

function showLoading(show) {
    const loadingIndicator = document.getElementById('loadingIndicator');
    if (show) {
        loadingIndicator.classList.remove('hidden');
    } else {
        loadingIndicator.classList.add('hidden');
    }
}

function showMessage(message, type) {
    const messageArea = document.getElementById('messageArea');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = type === 'error' ? 'error-message' : 'success-message';
    messageDiv.textContent = message;
    
    messageArea.innerHTML = '';
    messageArea.appendChild(messageDiv);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        if (messageArea.contains(messageDiv)) {
            messageArea.removeChild(messageDiv);
        }
    }, 5000);
}

// Utility functions
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// Export functions for global access
window.solveOptimization = solveOptimization;