"""
Enhanced processing: Calculate ALL metrics for interactive map.

Adds:
- Per-year averages (for slider)
- Trends per decade
- 2050 projections
- Rate of change

Usage:
    python scripts\\heat_analysis\\05_process_for_interactive_map.py
"""
import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

from config import DATA_PROCESSED, HEAT_THRESHOLDS, PROJECTION_YEARS

print("="*60)
print("PROCESSING DATA FOR INTERACTIVE MAP")
print("="*60)

# Load the corrected parquet data
print("\n1. Loading processed data...")
df = pd.read_parquet(DATA_PROCESSED / "heat_metrics_iberia.parquet")
print(f"   ✓ Loaded {len(df)} records")
print(f"   Years: {df['year'].min()} - {df['year'].max()}")

# Calculate per-year averages for each location (for slider)
print("\n2. Calculating per-year averages...")
yearly_avg = df.groupby(['lat', 'lon', 'year']).agg({
    'days_ge_moderate': 'mean',
    'days_ge_extreme': 'mean',
    'max_utci': 'max'
}).reset_index()

print(f"   ✓ {len(yearly_avg)} location-year combinations")

# Calculate trends for each location
print("\n3. Calculating trends per location...")

def calculate_trend(group):
    """Calculate linear trend for a location."""
    years = group['year'].values
    values = group['days_ge_moderate'].values
    
    if len(years) < 3:
        return pd.Series({
            'trend_per_decade': np.nan,
            'trend_p_value': np.nan,
            'baseline_avg': np.nan,
            'recent_avg': np.nan
        })
    
    slope, intercept, r, p, se = stats.linregress(years, values)
    
    # Baseline (first 2 years) vs recent (last 2 years)
    baseline = group[group['year'] <= group['year'].min() + 1]['days_ge_moderate'].mean()
    recent = group[group['year'] >= group['year'].max() - 1]['days_ge_moderate'].mean()
    
    return pd.Series({
        'trend_per_decade': slope * 10,
        'trend_p_value': p,
        'baseline_avg': baseline,
        'recent_avg': recent
    })

trends = df.groupby(['lat', 'lon']).apply(calculate_trend).reset_index()

print(f"   ✓ Calculated trends for {len(trends)} locations")
print(f"   Trend range: {trends['trend_per_decade'].min():.1f} to {trends['trend_per_decade'].max():.1f} days/decade")

# Calculate 2050 projection for each location
print("\n4. Calculating 2050 projections...")

def calculate_projection(group):
    """Project to 2050 using linear trend."""
    years = group['year'].values
    values = group['days_ge_moderate'].values
    
    if len(years) < 3:
        return pd.Series({'projected_2050': np.nan})
    
    slope, intercept, _, _, _ = stats.linregress(years, values)
    projection = slope * 2050 + intercept
    
    return pd.Series({'projected_2050': max(0, projection)})

projections = df.groupby(['lat', 'lon']).apply(calculate_projection).reset_index()

print(f"   ✓ Calculated projections for {len(projections)} locations")
print(f"   2050 range: {projections['projected_2050'].min():.1f} to {projections['projected_2050'].max():.1f} days")

# Calculate rate of change (%)
print("\n5. Calculating rate of change...")
trends['rate_of_change_pct'] = ((trends['recent_avg'] - trends['baseline_avg']) / 
                                 trends['baseline_avg'].replace(0, np.nan)) * 100

print(f"   ✓ Rate of change range: {trends['rate_of_change_pct'].min():.1f}% to {trends['rate_of_change_pct'].max():.1f}%")

# Combine all metrics
print("\n6. Combining all metrics...")
final = trends.merge(projections, on=['lat', 'lon'])

# Add current average (last 3 years)
current_avg = df[df['year'] >= df['year'].max() - 2].groupby(['lat', 'lon']).agg({
    'days_ge_moderate': 'mean',
    'days_ge_extreme': 'mean',
    'max_utci': 'max'
}).reset_index()

current_avg.columns = ['lat', 'lon', 'current_days_moderate', 'current_days_extreme', 'current_max_utci']

final = final.merge(current_avg, on=['lat', 'lon'])

# Save enhanced dataset
output_file = DATA_PROCESSED / "heat_metrics_enhanced.parquet"
print(f"\n7. Saving enhanced dataset...")
final.to_parquet(output_file, compression='snappy')

# Also save yearly data for slider
yearly_file = DATA_PROCESSED / "heat_metrics_yearly.parquet"
yearly_avg.to_parquet(yearly_file, compression='snappy')

print(f"\n{'='*60}")
print(f"SUCCESS")
print(f"{'='*60}")
print(f"Enhanced metrics: {output_file}")
print(f"  - Rows: {len(final)}")
print(f"  - Columns: {list(final.columns)}")
print(f"\nYearly data: {yearly_file}")
print(f"  - Rows: {len(yearly_avg)}")
print(f"  - Years: {sorted(yearly_avg['year'].unique())}")
print(f"\n{'='*60}")
print("Ready to create interactive map!")
print(f"{'='*60}")