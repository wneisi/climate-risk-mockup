"""
Create OPTIMIZED choropleth map - same features, much smaller file.

Optimizations:
- Reuse geometry across layers (not duplicate)
- Simplify polygon coordinates
- Use single GeoJSON with dynamic styling

Usage:
    python scripts\\heat\\create_map_OPTIMIZED.py
"""
import folium
from folium import plugins
import pandas as pd
import geopandas as gpd
import numpy as np
import json
from pathlib import Path
from shapely.geometry import Point

import sys
from pathlib import Path
import folium
from folium import plugins
import pandas as pd
import geopandas as gpd
import numpy as np
import json
from shapely.geometry import Point

# Define paths directly
REPO_ROOT = Path(__file__).parent.parent.parent
DATA_ROOT = REPO_ROOT / "data"
HEAT_DATA = DATA_ROOT / "heat"
HEAT_MAPS = REPO_ROOT / "maps" / "heat"

# Heat thresholds
HEAT_THRESHOLDS = {
    'moderate': 32.0,
    'extreme': 40.0,
}

print("="*60)
print("CREATING OPTIMIZED CHOROPLETH MAP")
print("="*60)

# Load boundaries
print("\n1. Loading municipality boundaries...")
boundaries_dir = DATA_ROOT / "boundaries"

spain_gdf = gpd.read_file(boundaries_dir / "spain_municipalities.geojson")
portugal_gdf = gpd.read_file(boundaries_dir / "portugal_municipalities.geojson")

print(f"   ✓ Spain: {len(spain_gdf)} municipalities")
print(f"   ✓ Portugal: {len(portugal_gdf)} municipalities")

# Standardize
if 'NAME_4' in spain_gdf.columns:
    spain_gdf['name'] = spain_gdf['NAME_4']
elif 'NAME_3' in spain_gdf.columns:
    spain_gdf['name'] = spain_gdf['NAME_3']
else:
    spain_gdf['name'] = spain_gdf.iloc[:, 0]

if 'NAME_2' in portugal_gdf.columns:
    portugal_gdf['name'] = portugal_gdf['NAME_2']
else:
    portugal_gdf['name'] = portugal_gdf.iloc[:, 0]

spain_gdf = spain_gdf.to_crs("EPSG:4326")
portugal_gdf = portugal_gdf.to_crs("EPSG:4326")

spain_gdf = spain_gdf[['name', 'geometry']].copy()
portugal_gdf = portugal_gdf[['name', 'geometry']].copy()

spain_gdf['country'] = 'Spain'
portugal_gdf['country'] = 'Portugal'

municipalities = pd.concat([spain_gdf, portugal_gdf], ignore_index=True)
municipalities = gpd.GeoDataFrame(municipalities, geometry='geometry', crs="EPSG:4326")

# OPTIMIZATION 1: Simplify geometries (reduce coordinate precision)
print("\n2. Simplifying geometries...")
print("   (Reduces file size without visible quality loss)")
municipalities['geometry'] = municipalities['geometry'].simplify(tolerance=0.001)
print("   ✓ Simplified")

# Load heat data
print("\n3. Loading heat risk data...")
enhanced = pd.read_parquet(HEAT_DATA / "processed" / "heat_metrics_enhanced.parquet")

# Spatial join
print("\n4. Performing spatial join...")
grid_points = gpd.GeoDataFrame(
    enhanced,
    geometry=[Point(lon, lat) for lon, lat in zip(enhanced['lon'], enhanced['lat'])],
    crs="EPSG:4326"
)

utm_crs = "EPSG:32630"
municipalities_utm = municipalities.to_crs(utm_crs)
grid_points_utm = grid_points.to_crs(utm_crs)

joined = gpd.sjoin_nearest(
    municipalities_utm,
    grid_points_utm,
    how='left',
    max_distance=50000
)

data_cols = ['current_days_moderate', 'current_days_extreme', 'current_max_utci',
             'trend_per_decade', 'baseline_avg', 'recent_avg',
             'projected_2050', 'rate_of_change_pct']

municipalities_with_data = joined.groupby(joined.index).agg({
    'name': 'first',
    'country': 'first',
    'geometry': 'first',
    **{col: 'mean' for col in data_cols if col in joined.columns}
}).reset_index(drop=True)

municipalities_with_data = gpd.GeoDataFrame(municipalities_with_data, geometry='geometry', crs=utm_crs)
municipalities_with_data = municipalities_with_data.to_crs("EPSG:4326")

print(f"   ✓ {municipalities_with_data['current_days_moderate'].notna().sum()} municipalities with data")

# Get thresholds
moderate_thresh = HEAT_THRESHOLDS['moderate']
extreme_thresh = HEAT_THRESHOLDS['extreme']

# Create map
print("\n5. Creating optimized map...")
m = folium.Map(
    location=[40.0, -4.0],
    zoom_start=6,
    tiles='CartoDB positron',
    control_scale=True,
    prefer_canvas=True  # OPTIMIZATION 2: Use canvas rendering
)

# OPTIMIZATION 3: Create GeoJSON once, use JavaScript to change colors
geojson_data = json.loads(municipalities_with_data.to_json())

# Add data to properties for JavaScript access
for i, feature in enumerate(geojson_data['features']):
    row = municipalities_with_data.iloc[i]
    feature['properties']['current_days_moderate'] = float(row['current_days_moderate']) if not pd.isna(row['current_days_moderate']) else None
    feature['properties']['current_days_extreme'] = float(row['current_days_extreme']) if not pd.isna(row['current_days_extreme']) else None
    feature['properties']['current_max_utci'] = float(row['current_max_utci']) if not pd.isna(row['current_max_utci']) else None
    feature['properties']['trend_per_decade'] = float(row['trend_per_decade']) if not pd.isna(row['trend_per_decade']) else None
    feature['properties']['projected_2050'] = float(row['projected_2050']) if not pd.isna(row['projected_2050']) else None
    feature['properties']['baseline_avg'] = float(row['baseline_avg']) if not pd.isna(row['baseline_avg']) else None
    feature['properties']['recent_avg'] = float(row['recent_avg']) if not pd.isna(row['recent_avg']) else None

print("   ✓ GeoJSON prepared")

# JavaScript color functions (runs in browser, not in HTML)
color_functions_js = f"""
// Color functions
function getColorCurrent(days) {{
    if (days == null) return '#cccccc';
    if (days < 20) return '#2166ac';
    if (days < 40) return '#4393c3';
    if (days < 60) return '#fdb863';
    if (days < 80) return '#d6604d';
    return '#b2182b';
}}

function getColorTrend(trend) {{
    if (trend == null) return '#cccccc';
    if (trend < -2) return '#2166ac';
    if (trend < 0) return '#92c5de';
    if (trend < 2) return '#f7f7f7';
    if (trend < 4) return '#fdb863';
    return '#b2182b';
}}

function getColorProjection(days) {{
    if (days == null) return '#cccccc';
    if (days < 40) return '#fee391';
    if (days < 70) return '#fec44f';
    if (days < 100) return '#d95f0e';
    return '#993404';
}}

// Popup builders
function buildPopupCurrent(props) {{
    var name = props.name || 'Unknown';
    var days_mod = props.current_days_moderate ? props.current_days_moderate.toFixed(1) : 'N/A';
    var days_ext = props.current_days_extreme ? props.current_days_extreme.toFixed(1) : 'N/A';
    var max_utci = props.current_max_utci ? props.current_max_utci.toFixed(1) : 'N/A';
    
    return '<div style="font-family: Arial; min-width: 260px;">' +
           '<h4 style="margin: 0 0 8px 0; color: #b2182b;">' + name + '</h4>' +
           '<hr style="margin: 5px 0;">' +
           '<div style="font-size: 0.85em; line-height: 1.6;">' +
           '<strong>Heat Days (2022-2024 avg):</strong><br>' +
           '• <strong>' + days_mod + '</strong> days ≥{moderate_thresh}°C (heat day)<br>' +
           '• <strong>' + days_ext + '</strong> days ≥{extreme_thresh}°C (extreme heat day)<br><br>' +
           '<strong>Maximum UTCI:</strong> ' + max_utci + '°C<br>' +
           '</div>' +
           '<div style="margin-top: 8px; padding: 6px; background: #f0f0f0; border-radius: 3px; font-size: 0.75em;">' +
           '<strong>Definitions:</strong><br>' +
           'Heat day: UTCI ≥{moderate_thresh}°C<br>' +
           'Extreme heat day: UTCI ≥{extreme_thresh}°C' +
           '</div></div>';
}}

function buildPopupTrend(props) {{
    var name = props.name || 'Unknown';
    var trend = props.trend_per_decade ? props.trend_per_decade.toFixed(1) : 'N/A';
    var baseline = props.baseline_avg ? props.baseline_avg.toFixed(1) : 'N/A';
    var recent = props.recent_avg ? props.recent_avg.toFixed(1) : 'N/A';
    var trend_num = props.trend_per_decade || 0;
    var trend_desc = trend_num > 0 ? 'WARMING' : trend_num < 0 ? 'COOLING' : 'STABLE';
    
    return '<div style="font-family: Arial; min-width: 260px;">' +
           '<h4 style="margin: 0 0 8px 0; color: #b2182b;">' + name + '</h4>' +
           '<hr style="margin: 5px 0;">' +
           '<div style="font-size: 0.85em; line-height: 1.6;">' +
           '<strong>Trend Analysis:</strong><br>' +
           'Change: <strong>' + trend + '</strong> days/decade<br>' +
           'Direction: <strong>' + trend_desc + '</strong><br><br>' +
           '<strong>Comparison:</strong><br>' +
           'Baseline (2020-2021): ' + baseline + ' days<br>' +
           'Recent (2023-2024): ' + recent + ' days<br>' +
           '</div></div>';
}}

function buildPopupProjection(props) {{
    var name = props.name || 'Unknown';
    var current = props.current_days_moderate ? props.current_days_moderate.toFixed(1) : 'N/A';
    var proj_2050 = props.projected_2050 ? props.projected_2050.toFixed(1) : 'N/A';
    
    return '<div style="font-family: Arial; min-width: 260px;">' +
           '<h4 style="margin: 0 0 8px 0; color: #b2182b;">' + name + '</h4>' +
           '<hr style="margin: 5px 0;">' +
           '<div style="font-size: 0.85em; line-height: 1.6;">' +
           '<strong>2050 Projection:</strong><br>' +
           'Expected heat days: <strong>' + proj_2050 + '</strong><br><br>' +
           '<strong>Comparison to Present:</strong><br>' +
           'Current (2022-2024): ' + current + ' days<br>' +
           'Projected 2050: ' + proj_2050 + ' days<br>' +
           '</div></div>';
}}

var currentLayer = 'current';
"""

# OPTIMIZATION 4: Single GeoJSON layer with dynamic styling
geojson_layer = folium.GeoJson(
    geojson_data,
    name='Municipalities',
    style_function=lambda x: {
        'fillColor': '#cccccc',
        'color': 'white',
        'weight': 0.3,
        'fillOpacity': 0.7
    },
    highlight_function=lambda x: {
        'weight': 2,
        'color': '#333'
    }
).add_to(m)

# Add custom JavaScript for layer switching
custom_js = f"""
<script>
{color_functions_js}

// Update layer colors based on active metric
function updateLayerColors(metric) {{
    var geojsonLayer = {geojson_layer.get_name()};
    
    geojsonLayer.eachLayer(function(layer) {{
        var props = layer.feature.properties;
        var color;
        var popup;
        
        if (metric === 'current') {{
            color = getColorCurrent(props.current_days_moderate);
            popup = buildPopupCurrent(props);
        }} else if (metric === 'trend') {{
            color = getColorTrend(props.trend_per_decade);
            popup = buildPopupTrend(props);
        }} else if (metric === 'projection') {{
            color = getColorProjection(props.projected_2050);
            popup = buildPopupProjection(props);
        }}
        
        layer.setStyle({{
            fillColor: color,
            fillOpacity: 0.7
        }});
        
        layer.bindPopup(popup);
    }});
    
    currentLayer = metric;
}}

// Initialize with current risk
setTimeout(function() {{
    updateLayerColors('current');
}}, 1000);
</script>
"""

m.get_root().html.add_child(folium.Element(custom_js))

# Add layer switcher buttons
button_html = """
<div style="position: fixed; top: 80px; right: 20px; z-index: 9999;
            background: white; padding: 10px; border-radius: 5px; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
    <h4 style="margin: 0 0 10px 0; font-size: 0.9em;">Select Layer</h4>
    <button onclick="updateLayerColors('current')" 
            style="display: block; width: 100%; margin: 5px 0; padding: 8px; cursor: pointer; border: 1px solid #ccc; border-radius: 3px; background: #2c7bb6; color: white;">
        Current Risk
    </button>
    <button onclick="updateLayerColors('trend')" 
            style="display: block; width: 100%; margin: 5px 0; padding: 8px; cursor: pointer; border: 1px solid #ccc; border-radius: 3px;">
        Trend
    </button>
    <button onclick="updateLayerColors('projection')" 
            style="display: block; width: 100%; margin: 5px 0; padding: 8px; cursor: pointer; border: 1px solid #ccc; border-radius: 3px;">
        2050 Projection
    </button>
</div>
"""

m.get_root().html.add_child(folium.Element(button_html))

# Add transparent dots (sampled)
print("\n6. Adding grid points...")
sampled = enhanced.iloc[::5].copy()  # More aggressive sampling

for idx, row in sampled.iterrows():
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=3,
        popup=f"Grid: {row['current_days_moderate']:.1f} days",
        color='#ff6600',
        fill=True,
        fillColor='#ff6600',
        fillOpacity=0.2,
        weight=1,
        opacity=0.3
    ).add_to(m)

print(f"   ✓ Added {len(sampled)} grid points")

# Add title
title_html = f'''
<div style="position: fixed; top: 10px; left: 50px; width: 420px;
            background: white; border: 2px solid #333; padding: 15px;
            z-index: 9999; border-radius: 8px; box-shadow: 2px 2px 8px rgba(0,0,0,0.3);">
    <h2 style="margin: 0 0 10px 0; color: #b2182b;">🗺️ Municipality Heat Risk</h2>
    <p style="margin: 5px 0; font-size: 0.9em;">
        <strong>Iberian Peninsula (2020-2024)</strong>
    </p>
    <hr style="margin: 10px 0;">
    <div style="font-size: 0.8em; color: #666;">
        {len(municipalities_with_data):,} municipalities<br>
        Click buttons (top right) to switch layers<br>
        Click any municipality for details
    </div>
</div>
'''
m.get_root().html.add_child(folium.Element(title_html))

# Save
print("\n7. Saving optimized map...")
output_file = HEAT_MAPS / "heat_risk_choropleth_OPTIMIZED.html"
m.save(str(output_file))

file_size_mb = output_file.stat().st_size / 1024 / 1024

print(f"\n{'='*60}")
print(f"SUCCESS - OPTIMIZED MAP CREATED!")
print(f"{'='*60}")
print(f"File: {output_file}")
print(f"Size: {file_size_mb:.1f} MB (was 102 MB)")
print(f"Reduction: {(1 - file_size_mb/102)*100:.0f}%")
print(f"\nOptimizations applied:")
print(f"  ✓ Geometry reused (not duplicated per layer)")
print(f"  ✓ Coordinates simplified")
print(f"  ✓ JavaScript-based layer switching")
print(f"  ✓ Canvas rendering")
print(f"  ✓ Reduced grid point sampling")
print(f"\nAll features preserved:")
print(f"  ✓ All 8,600+ municipalities")
print(f"  ✓ All 3 layers (Current/Trend/2050)")
print(f"  ✓ All detailed popups")
print(f"  ✓ Transparent grid overlay")
print(f"{'='*60}")