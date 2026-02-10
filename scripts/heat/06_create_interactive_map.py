"""
Create fully interactive heat risk map with:
- Time slider (2020-2024)
- Trend heatmap
- 2050 projection heatmap  
- Rate of change heatmap
- Toggle controls

Usage:
    python scripts\\heat_analysis\\06_create_interactive_map.py
"""
import folium
from folium import plugins
import pandas as pd
import numpy as np
import json
from pathlib import Path

from config import DATA_PROCESSED, HEAT_THRESHOLDS, MAPS_DIR

print("="*60)
print("CREATING INTERACTIVE HEAT RISK MAP")
print("="*60)

# Load data
print("\n1. Loading data...")
enhanced = pd.read_parquet(DATA_PROCESSED / "heat_metrics_enhanced.parquet")
yearly = pd.read_parquet(DATA_PROCESSED / "heat_metrics_yearly.parquet")

print(f"   ✓ Enhanced data: {len(enhanced)} locations")
print(f"   ✓ Yearly data: {len(yearly)} records")
print(f"   ✓ Years available: {sorted(yearly['year'].unique())}")

# Create base map
print("\n2. Creating base map...")
center_lat = (enhanced['lat'].min() + enhanced['lat'].max()) / 2
center_lon = (enhanced['lon'].min() + enhanced['lon'].max()) / 2

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=6,
    tiles='CartoDB positron',
    control_scale=True
)

# Prepare data for heatmaps
print("\n3. Preparing heatmap data...")

def create_heatmap_data(df, value_col, lat_col='lat', lon_col='lon'):
    """Convert dataframe to heatmap format."""
    data = []
    for _, row in df.iterrows():
        if not pd.isna(row[value_col]):
            data.append([row[lat_col], row[lon_col], row[value_col]])
    return data

# Current conditions heatmap
current_data = create_heatmap_data(enhanced, 'current_days_moderate')

# Trend heatmap
trend_data = create_heatmap_data(enhanced, 'trend_per_decade')

# 2050 projection heatmap
projection_data = create_heatmap_data(enhanced, 'projected_2050')

# Rate of change heatmap
rate_data = create_heatmap_data(enhanced, 'rate_of_change_pct')

# Yearly data for slider
yearly_by_year = {}
for year in sorted(yearly['year'].unique()):
    year_df = yearly[yearly['year'] == year]
    yearly_by_year[int(year)] = create_heatmap_data(year_df, 'days_ge_moderate')

print(f"   ✓ Prepared {len(current_data)} points for current conditions")
print(f"   ✓ Prepared {len(trend_data)} points for trends")
print(f"   ✓ Prepared {len(projection_data)} points for projections")
print(f"   ✓ Prepared {len(yearly_by_year)} years for slider")

# Add heatmap layers
print("\n4. Adding heatmap layers...")

# Layer 1: Current Risk (2022-2024 average)
heatmap_current = plugins.HeatMap(
    current_data,
    name='Current Risk (2022-2024 avg)',
    min_opacity=0.4,
    max_opacity=0.8,
    radius=25,
    blur=20,
    gradient={0.0: 'green', 0.3: 'yellow', 0.6: 'orange', 0.8: 'red', 1.0: 'darkred'},
    show=True
)
heatmap_current.add_to(m)

# Layer 2: Trend Map
# Normalize trend data (can be negative or positive)
trend_normalized = [[d[0], d[1], (d[2] + 10) / 20] for d in trend_data if not np.isnan(d[2])]

heatmap_trend = plugins.HeatMap(
    trend_normalized,
    name='Trend (days/decade)',
    min_opacity=0.4,
    max_opacity=0.8,
    radius=25,
    blur=20,
    gradient={0.0: 'blue', 0.3: 'lightblue', 0.5: 'white', 0.7: 'orange', 1.0: 'darkred'},
    show=False
)
heatmap_trend.add_to(m)

# Layer 3: 2050 Projection
heatmap_2050 = plugins.HeatMap(
    projection_data,
    name='2050 Projection',
    min_opacity=0.4,
    max_opacity=0.8,
    radius=25,
    blur=20,
    gradient={0.0: 'yellow', 0.5: 'orange', 0.8: 'red', 1.0: 'darkred'},
    show=False
)
heatmap_2050.add_to(m)

# Layer 4: Rate of Change
# Normalize rate (can be large positive numbers)
rate_normalized = [[d[0], d[1], min(d[2] / 100, 1.0)] for d in rate_data if not np.isnan(d[2])]

heatmap_rate = plugins.HeatMap(
    rate_normalized,
    name='Rate of Change (%)',
    min_opacity=0.4,
    max_opacity=0.8,
    radius=25,
    blur=20,
    gradient={0.0: 'white', 0.3: 'lightyellow', 0.6: 'orange', 1.0: 'darkred'},
    show=False
)
heatmap_rate.add_to(m)

# Add layer control
print("\n5. Adding layer controls...")
folium.LayerControl(position='topright', collapsed=False).add_to(m)

# Add time slider
print("\n6. Adding time slider...")

slider_html = f'''
<div id="slider-container" style="position: fixed; bottom: 50px; left: 50%; transform: translateX(-50%);
                                  background: white; padding: 20px; border-radius: 10px; 
                                  box-shadow: 0 4px 6px rgba(0,0,0,0.3); z-index: 9999;
                                  min-width: 400px; display: none;">
    <h4 style="margin: 0 0 15px 0; text-align: center;">Time Evolution</h4>
    <div style="display: flex; align-items: center; gap: 10px;">
        <button id="play-btn" style="padding: 5px 15px; cursor: pointer;">▶ Play</button>
        <input type="range" id="year-slider" min="2020" max="2024" value="2020" step="1" 
               style="flex: 1; height: 8px;">
        <span id="year-display" style="font-weight: bold; min-width: 50px;">2020</span>
    </div>
    <div id="year-info" style="margin-top: 10px; font-size: 0.9em; color: #666; text-align: center;">
        Average heat days: <span id="year-stat">--</span>
    </div>
</div>

<script>
var yearlyData = {json.dumps(yearly_by_year)};
var currentHeatmap = null;
var isPlaying = false;
var playInterval = null;

function updateHeatmap(year) {{
    // Remove old heatmap
    if (currentHeatmap) {{
        map.removeLayer(currentHeatmap);
    }}
    
    // Add new heatmap for this year
    var data = yearlyData[year];
    if (data) {{
        currentHeatmap = L.heatLayer(data, {{
            radius: 25,
            blur: 20,
            maxOpacity: 0.8,
            gradient: {{0.0: 'green', 0.3: 'yellow', 0.6: 'orange', 0.8: 'red', 1.0: 'darkred'}}
        }}).addTo(map);
    }}
    
    // Update display
    document.getElementById('year-display').textContent = year;
    
    // Calculate average for this year
    if (data && data.length > 0) {{
        var sum = data.reduce((a, b) => a + b[2], 0);
        var avg = (sum / data.length).toFixed(1);
        document.getElementById('year-stat').textContent = avg + ' days';
    }}
}}

document.getElementById('year-slider').addEventListener('input', function(e) {{
    updateHeatmap(parseInt(e.target.value));
}});

document.getElementById('play-btn').addEventListener('click', function() {{
    if (isPlaying) {{
        clearInterval(playInterval);
        this.textContent = '▶ Play';
        isPlaying = false;
    }} else {{
        this.textContent = '⏸ Pause';
        isPlaying = true;
        
        playInterval = setInterval(function() {{
            var slider = document.getElementById('year-slider');
            var currentYear = parseInt(slider.value);
            var nextYear = currentYear + 1;
            
            if (nextYear > 2024) {{
                nextYear = 2020;
            }}
            
            slider.value = nextYear;
            updateHeatmap(nextYear);
        }}, 1500); // Change year every 1.5 seconds
    }}
}});

// Initialize with 2020
updateHeatmap(2020);
</script>
'''

m.get_root().html.add_child(folium.Element(slider_html))

# Add title and controls
print("\n7. Adding title and legends...")

title_html = f'''
<div style="position: fixed; top: 10px; left: 50px; width: 450px;
            background: white; border: 2px solid #333; padding: 15px;
            z-index: 9999; border-radius: 8px; box-shadow: 2px 2px 8px rgba(0,0,0,0.3);">
    <h2 style="margin: 0 0 10px 0; color: #d73027;">🌡️ Interactive Heat Risk Explorer</h2>
    <p style="margin: 5px 0; font-size: 0.95em;">
        <strong>Iberian Peninsula Climate Analysis (2020-2024)</strong>
    </p>
    <hr style="margin: 10px 0; border: none; border-top: 1px solid #ddd;">
    
    <div style="font-size: 0.85em; line-height: 1.6;">
        <strong>📊 Available Layers:</strong><br>
        • <span style="color: #d73027;">Current Risk</span> - Recent conditions (2022-2024)<br>
        • <span style="color: #4575b4;">Trend</span> - Change per decade<br>
        • <span style="color: #fc8d59;">2050 Projection</span> - Expected future<br>
        • <span style="color: #fee090;">Rate of Change</span> - % increase<br>
        
        <button id="toggle-slider" onclick="toggleSlider()" 
                style="margin-top: 10px; padding: 8px 15px; cursor: pointer; width: 100%;
                       background: #2c7bb6; color: white; border: none; border-radius: 4px;">
            🎬 Show Time Slider
        </button>
    </div>
    
    <p style="margin: 10px 0 0 0; font-size: 0.75em; color: #999;">
        Thresholds: {HEAT_THRESHOLDS['moderate']}°C / {HEAT_THRESHOLDS['extreme']}°C UTCI
    </p>
</div>

<script>
function toggleSlider() {{
    var slider = document.getElementById('slider-container');
    var btn = document.getElementById('toggle-slider');
    if (slider.style.display === 'none') {{
        slider.style.display = 'block';
        btn.textContent = '✖ Hide Time Slider';
        btn.style.background = '#d73027';
    }} else {{
        slider.style.display = 'none';
        btn.textContent = '🎬 Show Time Slider';
        btn.style.background = '#2c7bb6';
    }}
}}
</script>
'''

m.get_root().html.add_child(folium.Element(title_html))

# Add legends for each layer
legends_html = '''
<div style="position: fixed; bottom: 20px; right: 20px; width: 220px;
            background: white; border: 2px solid #333; padding: 12px;
            z-index: 9999; border-radius: 5px; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
    <h4 style="margin: 0 0 10px 0; font-size: 0.95em;">Legend</h4>
    
    <div style="font-size: 0.75em; line-height: 1.8;">
        <strong>Current Risk / Time Slider:</strong><br>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width: 15px; height: 15px; background: green; margin-right: 8px;"></div>
            Low (<30 days)
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width: 15px; height: 15px; background: orange; margin-right: 8px;"></div>
            Medium (30-60)
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width: 15px; height: 15px; background: darkred; margin-right: 8px;"></div>
            High (>60 days)
        </div>
        
        <hr style="margin: 8px 0; border: none; border-top: 1px solid #ddd;">
        
        <strong>Trend Map:</strong><br>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width: 15px; height: 15px; background: blue; margin-right: 8px;"></div>
            Cooling
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width: 15px; height: 15px; background: white; border: 1px solid #ccc; margin-right: 8px;"></div>
            Stable
        </div>
        <div style="display: flex; align-items: center; margin: 3px 0;">
            <div style="width: 15px; height: 15px; background: darkred; margin-right: 8px;"></div>
            Warming
        </div>
    </div>
</div>
'''

m.get_root().html.add_child(folium.Element(legends_html))

# Save map
print("\n8. Saving map...")
output_file = MAPS_DIR / "heat_risk_interactive.html"
m.save(str(output_file))

print(f"\n{'='*60}")
print(f"SUCCESS!")
print(f"{'='*60}")
print(f"Interactive map created: {output_file}")
print(f"File size: {output_file.stat().st_size / 1024:.0f} KB")
print(f"\nFeatures included:")
print(f"  ✓ 4 heatmap layers (current, trend, 2050, rate)")
print(f"  ✓ Time slider (2020-2024)")
print(f"  ✓ Layer toggle controls")
print(f"  ✓ Play/pause animation")
print(f"\nOpen in browser:")
print(f"  {output_file.absolute()}")
print(f"{'='*60}")