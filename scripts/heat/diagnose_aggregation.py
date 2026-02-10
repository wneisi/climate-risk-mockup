"""
Diagnose data aggregation issue.
"""
import pandas as pd
from config import DATA_PROCESSED

df = pd.read_parquet(DATA_PROCESSED / "heat_metrics_iberia.parquet")

print("="*60)
print("DATA DIAGNOSTIC")
print("="*60)

# Check one specific location
test_loc = df[(df['lat'] == 41.00) & (df['lon'] == 0.00)]

print(f"\nSample location: 41.00°N, 0.00°E")
print(f"Years available: {len(test_loc)}")
print(f"\nAnnual data:")
print(test_loc[['year', 'days_ge_moderate', 'days_ge_extreme']])

print(f"\nPer-year values:")
for _, row in test_loc.iterrows():
    print(f"  {row['year']}: {row['days_ge_moderate']:.1f} days ≥32°C")

print(f"\nCurrent aggregation in map script:")
recent = test_loc[test_loc['year'] >= test_loc['year'].max() - 2]
print(f"  Recent years: {list(recent['year'].values)}")
print(f"  Mean: {recent['days_ge_moderate'].mean():.1f} days")
print(f"  Sum (WRONG): {recent['days_ge_moderate'].sum():.1f} days")

print(f"\n{'='*60}")
print("CONCLUSION:")
print("If map shows ~520 days, it's summing 5 years instead of averaging!")
print("="*60)