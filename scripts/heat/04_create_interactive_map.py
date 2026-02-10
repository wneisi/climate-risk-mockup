"""
Create interactive heat risk map for GitHub Pages.

This creates a standalone HTML file that can be shared and hosted.

Usage:
    python scripts\\heat_analysis\\04_create_interactive_map.py
    
Output:
    maps/heat_risk_explorer.html
"""
import folium
from folium import IFrame
import pandas as pd
import numpy as np
from pathlib import Path

# Import from config
from config import DATA_PROCESSED, HEAT_THRESHOLDS, BBOX, MAPS_DIR

def load_summary_data():
    """Load and summarize data for map visualization."""
    
    print("Loading processed data...")
    df = pd.read_parquet(DATA_PROCESSED / "heat_metrics_iberia.parquet")
    
    print(f"Data loaded: {len(df)} records")
    
    # Calculate average metrics for most recent years
    recent_years = df[df['year'] >= df['year'].max() - 2]  # Last 3 years
    
    # Group by location and calculate averages
    summary = recent_years.groupby(['lat', 'lon']).agg({
        'days_ge_moderate': 'mean',
        'days_ge_extreme': 'mean',
        'max_utci': 'max'
    }).reset_index()
    
    print(f"Created summary for {len(summary)} grid cells")
    
    return summary

def create_heat_map():
    """Create interactive Folium map with heat risk data."""
    
    print("\nCreating interactive map...")
    
    # Load data
    summary_df = load_summary_data()
    
    # Center on Iberian Peninsula
    center_lat = (BBOX['north'] + BBOX['south']) / 2
    center_lon = (BBOX['east'] + BBOX['west']) / 2
    
    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=6,
        tiles='OpenStreetMap',
        control_scale=True
    )
    
    # Add title and instructions
    title_html = f'''
    <div style="position: fixed; 
                top: 10px; 
                left: 50px; 
                width: 400px;
                background-color: white; 
                border: 2px solid #333; 
                border-radius: 5px;
                z-index: 9999; 
                padding: 15px;
                font-family: Arial, sans-serif;
                box-shadow: 3px 3px 10px rgba(0,0,0,0.3);">
        <h2 style="margin: 0 0 10px 0; color: #d73027;">🌡️ Heat Risk Explorer</h2>
        <p style="margin: 5px 0; font-size: 0.95em;">
            <strong>Iberian Peninsula Climate Risk Analysis</strong>
        </p>
        <p style="margin: 5px 0; font-size: 0.85em; color: #666;">
            Click any marker to see detailed heat risk metrics
        </p>
        <hr style="margin: 10px 0; border: none; border-top: 1px solid #ddd;">
        <p style="margin: 5px 0; font-size: 0.8em;">
            📊 Data: ERA5-HEAT UTCI (2020-2024)<br>
            🌡️ Thresholds: {HEAT_THRESHOLDS['moderate']}°C / {HEAT_THRESHOLDS['extreme']}°C<br>
            🎯 Grid: 480 locations across Iberia
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Add heat layer - create color-coded markers
    print("Adding heat risk markers...")
    
    # Determine color based on heat days
    def get_color(days_moderate):
        if days_moderate < 20:
            return 'green'
        elif days_moderate < 50:
            return 'orange'
        elif days_moderate < 80:
            return 'red'
        else:
            return 'darkred'
    
    def get_radius(days_moderate):
        # Marker size based on heat intensity
        return 3 + (days_moderate / 20)
    
    # Sample grid to avoid overcrowding (every 3rd point)
    sampled = summary_df.iloc[::3].copy()
    
    print(f"Adding {len(sampled)} markers to map...")
    
    for idx, row in sampled.iterrows():
        lat = row['lat']
        lon = row['lon']
        days_mod = row['days_ge_moderate']
        days_ext = row['days_ge_extreme']
        max_temp = row['max_utci']
        
        # Create popup content
        popup_html = f'''
        <div style="font-family: Arial; width: 280px;">
            <h4 style="margin: 0 0 10px 0; color: #d73027; border-bottom: 2px solid #d73027; padding-bottom: 5px;">
                Heat Risk Report
            </h4>
            <p style="margin: 5px 0; font-size: 0.85em; color: #666;">
                <strong>Location:</strong> {lat:.2f}°N, {lon:.2f}°E
            </p>
            
            <h5 style="margin: 10px 0 5px 0; color: #333;">Recent Conditions (2022-2024 avg)</h5>
            <table style="width: 100%; font-size: 0.85em; border-collapse: collapse;">
                <tr>
                    <td style="padding: 3px;">Days ≥{HEAT_THRESHOLDS['moderate']}°C:</td>
                    <td style="padding: 3px; text-align: right;"><strong>{days_mod:.1f}</strong> days/year</td>
                </tr>
                <tr style="background: #f5f5f5;">
                    <td style="padding: 3px;">Days ≥{HEAT_THRESHOLDS['extreme']}°C:</td>
                    <td style="padding: 3px; text-align: right;"><strong>{days_ext:.1f}</strong> days/year</td>
                </tr>
                <tr>
                    <td style="padding: 3px;">Maximum UTCI:</td>
                    <td style="padding: 3px; text-align: right;"><strong>{max_temp:.1f}°C</strong></td>
                </tr>
            </table>
            
            <div style="margin-top: 10px; padding: 8px; background: #fff3cd; border-radius: 3px; font-size: 0.75em;">
                <strong>💡 Interpretation:</strong><br>
                {"🟢 Low risk - Moderate heat exposure" if days_mod < 20 else
                 "🟠 Medium risk - Significant heat days" if days_mod < 50 else
                 "🔴 High risk - Frequent extreme heat" if days_mod < 80 else
                 "🔥 Very High risk - Severe heat stress"}
            </div>
            
            <p style="margin: 10px 0 0 0; font-size: 0.7em; color: #999; border-top: 1px solid #ddd; padding-top: 5px;">
                Click coordinates in terminal for full analysis:<br>
                <code style="background: #f5f5f5; padding: 2px 4px; border-radius: 2px;">
                python scripts\\heat_analysis\\03_query_heat_risk.py {lat:.2f} {lon:.2f}
                </code>
            </p>
        </div>
        '''
        
        # Add circle marker
        folium.CircleMarker(
            location=[lat, lon],
            radius=get_radius(days_mod),
            popup=folium.Popup(popup_html, max_width=300),
            color=get_color(days_mod),
            fill=True,
            fillColor=get_color(days_mod),
            fillOpacity=0.6,
            weight=2
        ).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; 
                left: 50px; 
                width: 200px;
                background-color: white; 
                border: 2px solid #333; 
                border-radius: 5px;
                z-index: 9999; 
                padding: 10px;
                font-family: Arial, sans-serif;
                box-shadow: 3px 3px 10px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 10px 0; font-size: 0.95em;">Heat Risk Level</h4>
        <div style="font-size: 0.8em;">
            <div style="margin: 5px 0;">
                <span style="display: inline-block; width: 20px; height: 20px; 
                             background: green; border-radius: 50%; margin-right: 8px;"></span>
                <20 days (Low)
            </div>
            <div style="margin: 5px 0;">
                <span style="display: inline-block; width: 20px; height: 20px; 
                             background: orange; border-radius: 50%; margin-right: 8px;"></span>
                20-50 days (Medium)
            </div>
            <div style="margin: 5px 0;">
                <span style="display: inline-block; width: 20px; height: 20px; 
                             background: red; border-radius: 50%; margin-right: 8px;"></span>
                50-80 days (High)
            </div>
            <div style="margin: 5px 0;">
                <span style="display: inline-block; width: 20px; height: 20px; 
                             background: darkred; border-radius: 50%; margin-right: 8px;"></span>
                >80 days (Very High)
            </div>
        </div>
        <p style="font-size: 0.7em; color: #666; margin: 10px 0 0 0; border-top: 1px solid #ddd; padding-top: 5px;">
            Days per year with UTCI ≥32°C
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

def main():
    print("="*60)
    print("CREATING INTERACTIVE HEAT RISK MAP")
    print("="*60)
    
    # Create map
    m = create_heat_map()
    
    # Save
    output_file = MAPS_DIR / "heat_risk_explorer.html"
    m.save(str(output_file))
    
    print(f"\n{'='*60}")
    print(f"SUCCESS")
    print(f"{'='*60}")
    print(f"Map saved: {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024:.1f} KB")
    print(f"\nTo view:")
    print(f"  1. Open in browser: {output_file.absolute()}")
    print(f"  2. Or double-click the file in Explorer")
    print(f"\nTo share on GitHub:")
    print(f"  1. Commit and push to your repo")
    print(f"  2. Enable GitHub Pages (Settings → Pages)")
    print(f"  3. Share URL: https://YOUR-USERNAME.github.io/climate-risk-mockup/maps/heat_risk_explorer.html")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()