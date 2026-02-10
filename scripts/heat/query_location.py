"""
Query heat risk for any location.

Works with both test data (5 years) and full dataset (47 years).

Usage (from repo root):
    conda activate geo
    python scripts\\heat_analysis\\03_query_heat_risk.py 40.42 -3.70
"""
import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np
from scipy import stats

# Import from config in same folder
from config import DATA_PROCESSED, HEAT_THRESHOLDS, PROJECTION_YEARS

def load_data():
    """Load precomputed metrics."""
    parquet_file = DATA_PROCESSED / "heat_metrics_iberia.parquet"
    if not parquet_file.exists():
        print(f"✗ Data not found: {parquet_file}")
        print("  Run: python scripts\\heat_analysis\\02_precompute_annual_metrics.py --test")
        sys.exit(1)
    
    print("Loading data...", end='', flush=True)
    df = pd.read_parquet(parquet_file)
    print(" ✓")
    return df

def find_nearest(df, lat, lon):
    """Find nearest grid cell."""
    print(f"Finding nearest grid point to ({lat:.3f}, {lon:.3f})...", end='', flush=True)
    
    # Calculate distances
    distances = np.sqrt((df['lat'] - lat)**2 + (df['lon'] - lon)**2)
    nearest_idx = distances.idxmin()
    grid_lat = df.loc[nearest_idx, 'lat']
    grid_lon = df.loc[nearest_idx, 'lon']
    
    # Get time series for this location
    mask = (df['lat'] == grid_lat) & (df['lon'] == grid_lon)
    result = df[mask].sort_values('year').reset_index(drop=True)
    
    print(f" ✓ (grid: {grid_lat:.2f}, {grid_lon:.2f})")
    
    return result, grid_lat, grid_lon

def simple_trend(years, values):
    """Calculate linear trend."""
    slope, intercept, r, p, se = stats.linregress(years, values)
    return {
        'per_year': slope,
        'per_decade': slope * 10,
        'p_value': p,
        'significant': p < 0.05
    }

def simple_projection(years, values, target_year):
    """Linear projection with uncertainty."""
    slope, intercept, _, _, _ = stats.linregress(years, values)
    projected = slope * target_year + intercept
    
    # Rough uncertainty (95% CI)
    residuals = values - (slope * years + intercept)
    std_resid = np.std(residuals)
    ci = 1.96 * std_resid
    
    return {
        'year': target_year,
        'expected': max(0, projected),
        'low': max(0, projected - ci),
        'high': projected + ci
    }

def gev_return_period(values, event_value):
    """Simple GEV-based return period."""
    try:
        # Fit GEV
        shape, loc, scale = stats.genextreme.fit(values)
        
        # Return period
        p = stats.genextreme.cdf(event_value, shape, loc=loc, scale=scale)
        if p >= 1.0:
            return float('inf')
        
        return 1 / (1 - p)
    except:
        return None

def analyze(lat, lon):
    """Full analysis for a point."""
    
    print(f"\n{'='*60}")
    print(f"ANALYZING HEAT RISK")
    print(f"{'='*60}\n")
    
    # Load data
    df_all = load_data()
    
    # Extract location
    df, grid_lat, grid_lon = find_nearest(df_all, lat, lon)
    
    if len(df) < 3:
        print("✗ Insufficient data (need at least 3 years)")
        return
    
    # Warn if limited data
    if len(df) < 20:
        print(f"⚠ Note: Only {len(df)} years of data available")
        print(f"  Trends may not be statistically significant")
        print(f"  For full analysis, download 1979-2025 data (47 years)")
        print()
    
    print(f"Analyzing {len(df)} years of data...")
    
    # Get thresholds
    moderate = HEAT_THRESHOLDS['moderate']
    extreme = HEAT_THRESHOLDS['extreme']
    
    # Current (last 5 years average or all data if less)
    n_recent = min(5, len(df))
    recent = df[df['year'] >= df['year'].max() - n_recent + 1]
    current = {
        'days_moderate': recent['days_ge_moderate'].mean(),
        'days_extreme': recent['days_ge_extreme'].mean(),
        'max_3day': recent['max_3day_utci'].mean()
    }
    
    # Trends
    years = df['year'].values
    trend_moderate = simple_trend(years, df['days_ge_moderate'].values)
    trend_extreme = simple_trend(years, df['days_ge_extreme'].values)
    
    # Projections
    projections = []
    for target in PROJECTION_YEARS:
        proj_mod = simple_projection(years, df['days_ge_moderate'].values, target)
        proj_ext = simple_projection(years, df['days_ge_extreme'].values, target)
        projections.append({
            'year': target,
            'days_moderate': proj_mod['expected'],
            'days_extreme': proj_ext['expected']
        })
    
    # Return period (if we have recent data)
    latest_year = df['year'].max()
    if latest_year >= 2020:
        rp = gev_return_period(
            df['max_3day_utci'].values,
            df[df['year'] == latest_year]['max_3day_utci'].values[0]
        )
    else:
        rp = None
    
    # Display results
    print(f"\n{'='*60}")
    print(f"HEAT RISK ASSESSMENT")
    print(f"{'='*60}")
    print(f"Location: {lat:.3f}°N, {lon:.3f}°E")
    print(f"Grid cell: {grid_lat:.2f}°N, {grid_lon:.2f}°E")
    print(f"Thresholds: {moderate}°C (moderate), {extreme}°C (extreme)")
    
    print(f"\nCURRENT CONDITIONS (last {n_recent} year average):")
    print(f"  • Days ≥{moderate}°C: {current['days_moderate']:.1f} per year")
    print(f"  • Days ≥{extreme}°C: {current['days_extreme']:.1f} per year")
    print(f"  • Max 3-day mean: {current['max_3day']:.1f}°C")
    
    print(f"\nTRENDS ({df['year'].min()}-{df['year'].max()}):")
    sig_note = "" if len(df) >= 20 else " [⚠ limited data]"
    print(f"  • Days ≥{moderate}°C: {trend_moderate['per_decade']:+.1f} days/decade", end='')
    if trend_moderate['significant']:
        print(f" [SIGNIFICANT ✓]{sig_note}")
    else:
        print(f" [not significant]{sig_note}")
    
    print(f"  • Days ≥{extreme}°C: {trend_extreme['per_decade']:+.1f} days/decade", end='')
    if trend_extreme['significant']:
        print(f" [SIGNIFICANT ✓]{sig_note}")
    else:
        print(f" [not significant]{sig_note}")
    
    print(f"\nPROJECTIONS (extrapolated from {len(df)}-year trend):")
    for proj in projections:
        print(f"  • {proj['year']}: {proj['days_moderate']:.1f} days ≥{moderate}°C, {proj['days_extreme']:.1f} days ≥{extreme}°C")
    
    if rp:
        print(f"\nEXTREME EVENT ANALYSIS:")
        print(f"  • {latest_year} event: {rp:.1f}-year return period")
        print(f"    (based on max 3-day mean UTCI)")
    
    print(f"\n{'='*60}")
    print(f"NOTE: Thresholds can be changed in scripts\\heat_analysis\\config.py")
    if len(df) < 20:
        print(f"CAVEAT: Limited to {len(df)} years - download full dataset for robust trends")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("\n" + "="*60)
        print("HEAT RISK QUERY TOOL")
        print("="*60)
        print("\nUsage: python scripts\\heat_analysis\\03_query_heat_risk.py <lat> <lon>")
        print("\nExamples:")
        print("  python scripts\\heat_analysis\\03_query_heat_risk.py 40.42 -3.70    # Madrid")
        print("  python scripts\\heat_analysis\\03_query_heat_risk.py 38.72 -9.14    # Lisbon")
        print("  python scripts\\heat_analysis\\03_query_heat_risk.py 37.39 -5.98    # Seville")
        print("\n" + "="*60 + "\n")
        sys.exit(1)
    
    lat = float(sys.argv[1])
    lon = float(sys.argv[2])
    
    analyze(lat, lon)