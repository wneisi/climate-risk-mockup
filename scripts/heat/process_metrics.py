"""
Precompute annual heat metrics from HOURLY UTCI files.

CORRECTED: Handles hourly data properly (24 timesteps per file).

Usage:
    python scripts\\heat_analysis\\02_precompute_CORRECTED.py --test
"""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime

from config import (
    DATA_RAW, 
    DATA_PROCESSED, 
    HEAT_THRESHOLDS,
    YEARS
)

def process_year(year, moderate_thresh, extreme_thresh):
    """
    Process one year of HOURLY UTCI → annual metrics.
    
    KEY FIX: Each daily file has 24 hourly values.
    We need to: 1) Take daily max, 2) THEN count days.
    """
    year_dir = DATA_RAW / f"era5_utci_{year}"
    
    if not year_dir.exists():
        print(f"⚠ Missing folder for {year}: {year_dir}")
        return None
    
    print(f"Processing {year}... ", end='', flush=True)
    
    # Find all daily NetCDF files
    daily_files = sorted(year_dir.glob("ECMWF_utci_" + str(year) + "*.nc"))
    
    if len(daily_files) == 0:
        print(f"⚠ No daily files found")
        return None
    
    expected_days = 366 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 365
    
    if len(daily_files) < expected_days - 5:
        print(f"⚠ Incomplete ({len(daily_files)}/{expected_days} days)")
        return None
    
    print(f"loading {len(daily_files)} days...", end='', flush=True)
    
    try:
        # Open all daily files
        ds_list = []
        for daily_file in daily_files:
            try:
                ds_day = xr.open_dataset(daily_file, engine='netcdf4')
                ds_list.append(ds_day)
            except Exception as e:
                print(f"\n  Warning: Could not open {daily_file.name}: {e}")
                continue
        
        if not ds_list:
            print(f" ✗ Could not open any files")
            return None
        
        print(f"concatenating...", end='', flush=True)
        
        # Concatenate along time dimension (creates hourly timeseries)
        ds = xr.concat(ds_list, dim='time')
        
        print(f"resampling to daily...", end='', flush=True)
        
        # KEY FIX: Resample hourly data to daily maximum
        # This converts 24 hourly values per day → 1 daily maximum
        utci_hourly = ds['utci']
        
        # Convert to Celsius if needed
        if utci_hourly.max() > 200:  # Kelvin
            utci_hourly = utci_hourly - 273.15
        
        # Resample to daily maximum (this is the critical step!)
        utci_daily_max = utci_hourly.resample(time='1D').max()
        
        print(f"computing metrics...", end='', flush=True)
        
        # Now count DAYS (not hours!)
        days_ge_moderate = (utci_daily_max >= moderate_thresh).sum(dim='time')
        days_ge_extreme = (utci_daily_max >= extreme_thresh).sum(dim='time')
        max_utci = utci_daily_max.max(dim='time')
        
        # Summer average (June, July, August) - use daily max
        summer_mask = utci_daily_max.time.dt.month.isin([6, 7, 8])
        mean_summer_utci = utci_daily_max.sel(time=summer_mask).mean(dim='time')
        
        # 3-day rolling mean of daily maxima
        utci_3day = utci_daily_max.rolling(time=3, center=True).mean()
        max_3day_utci = utci_3day.max(dim='time')
        
        # Create metrics dataset
        metrics = xr.Dataset({
            'days_ge_moderate': days_ge_moderate.astype('int16'),
            'days_ge_extreme': days_ge_extreme.astype('int16'),
            'max_utci': max_utci.astype('float32'),
            'mean_summer_utci': mean_summer_utci.astype('float32'),
            'max_3day_utci': max_3day_utci.astype('float32'),
        })
        
        # Trigger computation
        metrics = metrics.compute()
        
        # Convert to DataFrame
        df = metrics.to_dataframe().reset_index()
        df['year'] = year
        
        # Close datasets
        for ds_day in ds_list:
            ds_day.close()
        ds.close()
        
        # Validation check
        max_days_mod = df['days_ge_moderate'].max()
        if max_days_mod > 365:
            print(f" ⚠ WARNING: Max days = {max_days_mod} (should be ≤365)")
            return None
        
        print(f" ✓ ({len(df)} cells, max {max_days_mod} days)")
        
        return df
        
    except Exception as e:
        print(f" ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true',
                       help='Process 2020-2024 only (test mode)')
    args = parser.parse_args()
    
    moderate = HEAT_THRESHOLDS['moderate']
    extreme = HEAT_THRESHOLDS['extreme']
    
    print(f"\n{'='*60}")
    print(f"PRECOMPUTING ANNUAL HEAT METRICS (CORRECTED)")
    print(f"{'='*60}")
    print(f"Thresholds: {moderate}°C (moderate), {extreme}°C (extreme)")
    print(f"Fix: Resampling hourly data to daily maxima")
    
    years_to_process = list(range(2020, 2025)) if args.test else YEARS
    print(f"Years: {years_to_process[0]}-{years_to_process[-1]} ({len(years_to_process)} total)")
    print(f"{'='*60}\n")
    
    all_data = []
    
    for i, year in enumerate(years_to_process):
        print(f"[{i+1}/{len(years_to_process)}] ", end='')
        df_year = process_year(year, moderate, extreme)
        if df_year is not None:
            all_data.append(df_year)
    
    if not all_data:
        print("\n✗ No data processed!")
        return
    
    # Combine all years
    print("\nCombining all years...")
    df_combined = pd.concat(all_data, ignore_index=True)
    
    # Validation
    print("\nValidation:")
    print(f"  Max days ≥{moderate}°C: {df_combined['days_ge_moderate'].max()}")
    print(f"  Max days ≥{extreme}°C: {df_combined['days_ge_extreme'].max()}")
    print(f"  Highest UTCI: {df_combined['max_utci'].max():.1f}°C")
    
    if df_combined['days_ge_moderate'].max() > 365:
        print("\n⚠ ERROR: Still seeing > 365 days! Data issue persists.")
        return
    
    # Save
    output_file = DATA_PROCESSED / "heat_metrics_iberia.parquet"
    print(f"\nSaving to {output_file}...")
    df_combined.to_parquet(output_file, compression='snappy')
    
    file_size_mb = output_file.stat().st_size / 1024 / 1024
    
    print(f"\n{'='*60}")
    print(f"SUCCESS")
    print(f"{'='*60}")
    print(f"Rows: {len(df_combined):,}")
    print(f"Years: {df_combined.year.min()} - {df_combined.year.max()}")
    print(f"Grid cells: {df_combined.groupby(['lat','lon']).ngroups}")
    print(f"File size: {file_size_mb:.1f} MB")
    print(f"Output: {output_file}")
    print(f"{'='*60}")
    print("\n✓ Ready to regenerate map!")
    print("  python scripts\\heat_analysis\\04_create_map_simple.py")

if __name__ == "__main__":
    main()