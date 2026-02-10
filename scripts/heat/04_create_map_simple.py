"""
Create simple interactive heat risk map.

Simplified version that guarantees markers are visible.

Usage:
    python scripts\\heat_analysis\\04_create_map_simple.py
"""
import folium
import pandas as pd
from pathlib import Path
from config import DATA_PROCESSED, HEAT_THRESHOLDS, MAPS_DIR

print("="*60)
print("CREATING HEAT RISK MAP (SIMPLE VERSION)")
print("="*60)

# Load data
print("\n1. Loading data...")
df = pd.read_parquet(DATA_PROCESSED / "heat_metrics_iberia.parquet")
print(f"   ✓ Loaded {len(df)} records")
print(f"   Years: {df['year'].min()} - {df['year'].max()}")
print(f"   Grid cells: {df.groupby(['lat','lon']).ngroups}")

# Get recent average
print("\n2. Calculating averages...")
recent = df[df['year'] >= df['year'].max() - 2]
summary = recent.groupby(['lat', 'lon']).agg({
    'days_ge_moderate': 'mean',
    'days_ge_extreme': 'mean',
    'max_utci': 'max'
}).reset_index()
print(f"   ✓ {len(summary)} unique locations")

# Sample every 2nd point to reduce clutter
summary = summary.iloc[::2].reset_index(drop=True)
print(f"   ✓ Sampled to {len(summary)} markers")

# Get bounds
lat_min, lat_max = summary['lat'].min(), summary['lat'].max()
lon_min, lon_max = summary['lon'].min(), summary['lon'].max()
print(f"   Bounds: {lat_min:.1f}°N to {lat_max:.1f}°N, {lon_min:.1f}°E to {lon_max:.1f}°E")

# Create map
print("\n3. Creating map...")
center_lat = (lat_min + lat_max) / 2
center_lon = (lon_min + lon_max) / 2

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=6,
    tiles='OpenStreetMap'
)

# Add title
title_html = '''
<div style="position: fixed; top: 10px; left: 50px; width: 350px;
            background: white; border: 2px solid #333; padding: 15px;
            z-index: 9999; border-radius: 5px; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
    <h3 style="margin: 0; color: #d73027;">🌡️ Heat Risk Explorer</h3>
    <p style="margin: 5px 0; font-size: 0.9em;"><strong>Iberian Peninsula (2020-2024)</strong></p>
    <p style="margin: 5px 0; font-size: 0.8em; color: #666;">
        Click markers for detailed heat metrics
    </p>
    <hr style="margin: 8px 0;">
    <p style="margin: 0; font-size: 0.75em; color: #666;">
        Thresholds: 32°C / 40°C UTCI
    </p>
</div>
'''
m.get_root().html.add_child(folium.Element(title_html))

# Add legend
legend_html = '''
<div style="position: fixed; bottom: 30px; left: 50px; width: 180px;
            background: white; border: 2px solid #333; padding: 10px;
            z-index: 9999; border-radius: 5px;">
    <h4 style="margin: 0 0 8px 0; font-size: 0.9em;">Heat Risk</h4>
    <div style="font-size: 0.75em;">
        <div><span style="color: green;">●</span> Low (<20 days)</div>
        <div><span style="color: orange;">●</span> Medium (20-50)</div>
        <div><span style="color: red;">●</span> High (50-80)</div>
        <div><span style="color: darkred;">●</span> Very High (>80)</div>
    </div>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# Add markers
print("\n4. Adding markers...")

def get_color(days):
    if days < 20: return 'green'
    elif days < 50: return 'orange'
    elif days < 80: return 'red'
    else: return 'darkred'

added = 0
for idx, row in summary.iterrows():
    lat = row['lat']
    lon = row['lon']
    days_mod = row['days_ge_moderate']
    days_ext = row['days_ge_extreme']
    max_t = row['max_utci']
    
    color = get_color(days_mod)
    
    # Simple popup
    popup_text = f"""
    <div style="font-family: Arial; min-width: 200px;">
        <b>Heat Risk Analysis</b><br>
        <hr style="margin: 5px 0;">
        📍 {lat:.2f}°N, {lon:.2f}°E<br>
        <br>
        <b>Recent Average (2022-2024):</b><br>
        • Days ≥32°C: <b>{days_mod:.1f}</b><br>
        • Days ≥40°C: <b>{days_ext:.1f}</b><br>
        • Max UTCI: <b>{max_t:.1f}°C</b><br>
        <br>
        <span style="color: {color};">
        <b>Risk Level: {
            'Low' if days_mod < 20 else
            'Medium' if days_mod < 50 else
            'High' if days_mod < 80 else
            'Very High'
        }</b>
        </span>
    </div>
    """
    
    folium.CircleMarker(
        location=[lat, lon],
        radius=5,
        popup=folium.Popup(popup_text, max_width=250),
        color=color,
        fill=True,
        fillColor=color,
        fillOpacity=0.7,
        weight=2
    ).add_to(m)
    
    added += 1
    if added % 50 == 0:
        print(f"   Added {added}/{len(summary)} markers...")

print(f"   ✓ Added all {added} markers")

# Fit bounds
print("\n5. Fitting map bounds...")
m.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])

# Save
output = MAPS_DIR / "heat_risk_explorer.html"
print(f"\n6. Saving map...")
m.save(str(output))

print(f"\n{'='*60}")
print(f"SUCCESS!")
print(f"{'='*60}")
print(f"Map created: {output}")
print(f"File size: {output.stat().st_size / 1024:.0f} KB")
print(f"\nOpen in browser:")
print(f"  {output.absolute()}")
print(f"{'='*60}")