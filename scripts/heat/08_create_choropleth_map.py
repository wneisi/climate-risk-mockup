"""
Create enhanced choropleth map with:
- Detailed popups for all layers
- Heat day definitions
- Legends for all metrics
- Transparent dots overlay

Usage:
    python scripts\\heat_analysis\\08_create_choropleth_ENHANCED.py
"""
import folium
from folium import plugins
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely.geometry import Point

from config import DATA_RAW, DATA_PROCESSED, HEAT_THRESHOLDS, MAPS_DIR

print("="*60)
print("CREATING ENHANCED MUNICIPALITY CHOROPLETH")
print("="*60)

# Load boundaries
print("\n1. Loading municipality boundaries...")
boundaries_dir = DATA_RAW / "boundaries"

spain_file = boundaries_dir / "spain_municipalities.geojson"
portugal_file = boundaries_dir / "portugal_municipalities.geojson"

if not spain_file.exists() or not portugal_file.exists():
    print("✗ Boundary files not found!")
    exit(1)

spain_gdf = gpd.read_file(spain_file)
portugal_gdf = gpd.read_file(portugal_file)

print(f"   ✓ Spain: {len(spain_gdf)} municipalities")
print(f"   ✓ Portugal: {len(portugal_gdf)} municipalities")

# Standardize: create 'name' column
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

# Ensure CRS
spain_gdf = spain_gdf.to_crs("EPSG:4326")
portugal_gdf = portugal_gdf.to_crs("EPSG:4326")

# Keep only essential columns
spain_gdf = spain_gdf[['name', 'geometry']].copy()
portugal_gdf = portugal_gdf[['name', 'geometry']].copy()

spain_gdf['country'] = 'Spain'
portugal_gdf['country'] = 'Portugal'

# Combine
municipalities = pd.concat([spain_gdf, portugal_gdf], ignore_index=True)
municipalities = gpd.GeoDataFrame(municipalities, geometry='geometry', crs="EPSG:4326")
print(f"   ✓ Total: {len(municipalities)} municipalities")

# Load heat data
print("\n2. Loading heat risk data...")
enhanced = pd.read_parquet(DATA_PROCESSED / "heat_metrics_enhanced.parquet")
print(f"   ✓ Grid points: {len(enhanced)}")

# Create point geometries
print("\n3. Performing spatial join...")
grid_points = gpd.GeoDataFrame(
    enhanced,
    geometry=[Point(lon, lat) for lon, lat in zip(enhanced['lon'], enhanced['lat'])],
    crs="EPSG:4326"
)

# Project to UTM
utm_crs = "EPSG:32630"
municipalities_utm = municipalities.to_crs(utm_crs)
grid_points_utm = grid_points.to_crs(utm_crs)

# Spatial join
joined = gpd.sjoin_nearest(
    municipalities_utm,
    grid_points_utm,
    how='left',
    max_distance=50000  # 50 km
)

# Aggregate
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

print(f"   ✓ Municipalities with data: {municipalities_with_data['current_days_moderate'].notna().sum()}")

# Get thresholds
moderate_thresh = HEAT_THRESHOLDS['moderate']
extreme_thresh = HEAT_THRESHOLDS['extreme']

# Create map
print("\n4. Creating base map...")
m = folium.Map(
    location=[40.0, -4.0],
    zoom_start=6,
    tiles='CartoDB positron',
    control_scale=True
)

# Color functions
def get_color_current(days):
    if pd.isna(days): return '#cccccc'
    if days < 20: return '#2166ac'
    elif days < 40: return '#4393c3'
    elif days < 60: return '#fdb863'
    elif days < 80: return '#d6604d'
    else: return '#b2182b'

def get_color_trend(trend):
    if pd.isna(trend): return '#cccccc'
    if trend < -2: return '#2166ac'
    elif trend < 0: return '#92c5de'
    elif trend < 2: return '#f7f7f7'
    elif trend < 4: return '#fdb863'
    else: return '#b2182b'

def get_color_projection(days):
    if pd.isna(days): return '#cccccc'
    if days < 40: return '#fee391'
    elif days < 70: return '#fec44f'
    elif days < 100: return '#d95f0e'
    else: return '#993404'

# Create popup function
def create_popup_current(row):
    """Create detailed popup for current risk."""
    name = row.get('name', 'Unknown')
    days_mod = row.get('current_days_moderate', np.nan)
    days_ext = row.get('current_days_extreme', np.nan)
    max_utci = row.get('current_max_utci', np.nan)
    
    return f"""
    <div style="font-family: Arial; min-width: 260px;">
        <h4 style="margin: 0 0 8px 0; color: #b2182b;">{name}</h4>
        <hr style="margin: 5px 0;">
        
        <div style="font-size: 0.85em; line-height: 1.6;">
            <strong>Heat Days (2022-2024 avg):</strong><br>
            • <strong>{days_mod:.1f}</strong> days ≥{moderate_thresh}°C (heat day)<br>
            • <strong>{days_ext:.1f}</strong> days ≥{extreme_thresh}°C (extreme heat day)<br>
            <br>
            <strong>Maximum UTCI:</strong> {max_utci:.1f}°C<br>
        </div>
        
        <div style="margin-top: 8px; padding: 6px; background: #f0f0f0; 
                    border-radius: 3px; font-size: 0.75em;">
            <strong>Definitions:</strong><br>
            Heat day: UTCI ≥{moderate_thresh}°C<br>
            Extreme heat day: UTCI ≥{extreme_thresh}°C
        </div>
    </div>
    """

def create_popup_trend(row):
    """Create detailed popup for trend."""
    name = row.get('name', 'Unknown')
    trend = row.get('trend_per_decade', np.nan)
    baseline = row.get('baseline_avg', np.nan)
    recent = row.get('recent_avg', np.nan)
    
    trend_desc = "warming" if trend > 0 else "cooling" if trend < 0 else "stable"
    
    return f"""
    <div style="font-family: Arial; min-width: 260px;">
        <h4 style="margin: 0 0 8px 0; color: #b2182b;">{name}</h4>
        <hr style="margin: 5px 0;">
        
        <div style="font-size: 0.85em; line-height: 1.6;">
            <strong>Trend Analysis:</strong><br>
            Change: <strong>{trend:+.1f}</strong> days/decade<br>
            Direction: <strong>{trend_desc.upper()}</strong><br>
            <br>
            <strong>Comparison:</strong><br>
            Baseline (2020-2021): {baseline:.1f} days<br>
            Recent (2023-2024): {recent:.1f} days<br>
            Change: <strong>{recent - baseline:+.1f}</strong> days
        </div>
        
        <div style="margin-top: 8px; padding: 6px; background: #f0f0f0; 
                    border-radius: 3px; font-size: 0.75em;">
            Based on linear trend (2020-2024)
        </div>
    </div>
    """

def create_popup_projection(row):
    """Create detailed popup for 2050 projection."""
    name = row.get('name', 'Unknown')
    current = row.get('current_days_moderate', np.nan)
    proj_2050 = row.get('projected_2050', np.nan)
    
    increase = proj_2050 - current
    pct_increase = (increase / current * 100) if current > 0 else 0
    
    return f"""
    <div style="font-family: Arial; min-width: 260px;">
        <h4 style="margin: 0 0 8px 0; color: #b2182b;">{name}</h4>
        <hr style="margin: 5px 0;">
        
        <div style="font-size: 0.85em; line-height: 1.6;">
            <strong>2050 Projection:</strong><br>
            Expected heat days: <strong>{proj_2050:.1f}</strong><br>
            <br>
            <strong>Comparison to Present:</strong><br>
            Current (2022-2024): {current:.1f} days<br>
            Projected 2050: {proj_2050:.1f} days<br>
            <br>
            <strong>Expected Change:</strong><br>
            +{increase:.1f} days ({pct_increase:+.0f}%)
        </div>
        
        <div style="margin-top: 8px; padding: 6px; background: #fff3cd; 
                    border-radius: 3px; font-size: 0.75em;">
            ⚠️ Linear extrapolation from 2020-2024 trend
        </div>
    </div>
    """

# Convert to GeoJSON
geojson_data = municipalities_with_data.__geo_interface__

# Create layers
print("\n5. Creating choropleth layers...")

# Layer 1: Current Risk
print("   Current Risk...", end='', flush=True)
feature_group_current = folium.FeatureGroup(name='Current Risk', show=True)

for idx, row in municipalities_with_data.iterrows():
    folium.GeoJson(
        row['geometry'].__geo_interface__,
        style_function=lambda x, days=row.get('current_days_moderate'): {
            'fillColor': get_color_current(days),
            'color': 'white',
            'weight': 0.3,
            'fillOpacity': 0.7
        },
        popup=folium.Popup(create_popup_current(row), max_width=300)
    ).add_to(feature_group_current)

feature_group_current.add_to(m)
print(" ✓")

# Layer 2: Trend
print("   Trend...", end='', flush=True)
feature_group_trend = folium.FeatureGroup(name='Trend (days/decade)', show=False)

for idx, row in municipalities_with_data.iterrows():
    folium.GeoJson(
        row['geometry'].__geo_interface__,
        style_function=lambda x, trend=row.get('trend_per_decade'): {
            'fillColor': get_color_trend(trend),
            'color': 'white',
            'weight': 0.3,
            'fillOpacity': 0.7
        },
        popup=folium.Popup(create_popup_trend(row), max_width=300)
    ).add_to(feature_group_trend)

feature_group_trend.add_to(m)
print(" ✓")

# Layer 3: 2050 Projection
print("   2050 Projection...", end='', flush=True)
feature_group_2050 = folium.FeatureGroup(name='2050 Projection', show=False)

for idx, row in municipalities_with_data.iterrows():
    folium.GeoJson(
        row['geometry'].__geo_interface__,
        style_function=lambda x, days=row.get('projected_2050'): {
            'fillColor': get_color_projection(days),
            'color': 'white',
            'weight': 0.3,
            'fillOpacity': 0.7
        },
        popup=folium.Popup(create_popup_projection(row), max_width=300)
    ).add_to(feature_group_2050)

feature_group_2050.add_to(m)
print(" ✓")

# Add transparent dots
print("\n6. Adding transparent grid points...")
sampled = enhanced.iloc[::3].copy()

for idx, row in sampled.iterrows():
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=3,
        popup=folium.Popup(f"""
            <div style="font-family: Arial; min-width: 180px;">
                <b>Grid Point Data</b><br>
                {row['lat']:.2f}°N, {row['lon']:.2f}°E<br>
                <hr style="margin: 4px 0;">
                Heat days: <b>{row['current_days_moderate']:.1f}</b><br>
                Extreme: <b>{row['current_days_extreme']:.1f}</b><br>
                Trend: <b>{row['trend_per_decade']:+.1f}</b>/decade<br>
                2050: <b>{row['projected_2050']:.1f}</b> days
            </div>
        """, max_width=220),
        color='#ff6600',
        fill=True,
        fillColor='#ff6600',
        fillOpacity=0.25,
        weight=1,
        opacity=0.4
    ).add_to(m)

print(f"   ✓ Added {len(sampled)} transparent markers")

# Controls
print("\n7. Adding controls and legends...")
folium.LayerControl(position='topright', collapsed=False).add_to(m)

# Title
title_html = f'''
<div style="position: fixed; top: 10px; left: 50px; width: 420px;
            background: white; border: 2px solid #333; padding: 15px;
            z-index: 9999; border-radius: 8px; box-shadow: 2px 2px 8px rgba(0,0,0,0.3);">
    <h2 style="margin: 0 0 10px 0; color: #b2182b;">🗺️ Municipality Heat Risk</h2>
    <p style="margin: 5px 0; font-size: 0.9em;">
        <strong>Iberian Peninsula (2020-2024)</strong>
    </p>
    <hr style="margin: 10px 0;">
    
    <div style="font-size: 0.8em; color: #666; line-height: 1.5;">
        <strong>Coverage:</strong> {len(municipalities_with_data):,} municipalities<br>
        <strong>Click any municipality</strong> for detailed metrics<br>
        <strong>Orange dots:</strong> Grid data points
    </div>
    
    <div style="margin-top: 10px; padding: 8px; background: #e8f4f8; 
                border-radius: 4px; font-size: 0.75em;">
        <strong>Definitions:</strong><br>
        • Heat day: UTCI ≥{moderate_thresh}°C<br>
        • Extreme heat day: UTCI ≥{extreme_thresh}°C
    </div>
</div>
'''
m.get_root().html.add_child(folium.Element(title_html))

# Comprehensive Legend
legend_html = '''
<div style="position: fixed; bottom: 30px; right: 20px; width: 220px;
            background: white; border: 2px solid #333; padding: 12px;
            z-index: 9999; border-radius: 5px; font-size: 0.8em;">
    
    <!-- Current Risk Legend -->
    <div id="legend-current">
        <h4 style="margin: 0 0 8px 0; font-size: 0.95em;">Current Risk</h4>
        <div style="font-size: 0.8em; line-height: 1.6;">
            <div>🔵 <20 heat days/year</div>
            <div>🟦 20-40 days</div>
            <div>🟠 40-60 days</div>
            <div>🔴 60-80 days</div>
            <div>🔥 >80 days</div>
        </div>
    </div>
    
    <!-- Trend Legend -->
    <div id="legend-trend" style="display: none;">
        <h4 style="margin: 0 0 8px 0; font-size: 0.95em;">Trend (days/decade)</h4>
        <div style="font-size: 0.8em; line-height: 1.6;">
            <div>🔵 Strong cooling (<-2)</div>
            <div>🟦 Slight cooling (0 to -2)</div>
            <div>⚪ Stable (±2)</div>
            <div>🟠 Warming (+2 to +4)</div>
            <div>🔴 Strong warming (>+4)</div>
        </div>
    </div>
    
    <!-- 2050 Projection Legend -->
    <div id="legend-2050" style="display: none;">
        <h4 style="margin: 0 0 8px 0; font-size: 0.95em;">2050 Projection</h4>
        <div style="font-size: 0.8em; line-height: 1.6;">
            <div>🟡 <40 days</div>
            <div>🟠 40-70 days</div>
            <div>🔶 70-100 days</div>
            <div>🔴 >100 days</div>
        </div>
        <div style="margin-top: 6px; font-size: 0.7em; color: #666;">
            Expected heat days/year
        </div>
    </div>
    
</div>

<script>
// Show/hide legends based on active layer
document.addEventListener('DOMContentLoaded', function() {
    // Monitor layer changes
    var observer = new MutationObserver(function(mutations) {
        var layers = document.querySelectorAll('.leaflet-control-layers-overlays input');
        var currentActive = false;
        var trendActive = false;
        var projection2050Active = false;
        
        layers.forEach(function(layer) {
            var label = layer.nextSibling.textContent.trim();
            if (layer.checked) {
                if (label.includes('Current')) currentActive = true;
                if (label.includes('Trend')) trendActive = true;
                if (label.includes('2050')) projection2050Active = true;
            }
        });
        
        document.getElementById('legend-current').style.display = currentActive ? 'block' : 'none';
        document.getElementById('legend-trend').style.display = trendActive ? 'block' : 'none';
        document.getElementById('legend-2050').style.display = projection2050Active ? 'block' : 'none';
    });
    
    observer.observe(document.body, { subtree: true, attributes: true });
});
</script>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# Save
print("\n8. Saving map...")
output_file = MAPS_DIR / "heat_risk_choropleth.html"
m.save(str(output_file))

file_size_mb = output_file.stat().st_size / 1024 / 1024

print(f"\n{'='*60}")
print(f"SUCCESS!")
print(f"{'='*60}")
print(f"File: {output_file}")
print(f"Size: {file_size_mb:.1f} MB")
print(f"\nEnhancements:")
print(f"  ✓ Detailed popups for all municipalities")
print(f"  ✓ Heat day definitions included")
print(f"  ✓ Extreme heat days shown")
print(f"  ✓ Dynamic legends (change with layers)")
print(f"\nOpen in browser:")
print(f"  {output_file.absolute()}")
print(f"{'='*60}")