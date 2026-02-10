"""
Download ERA5-HEAT UTCI data for multiple years.

Based on actual Copernicus CDS web form API code.

Usage (from repo root):
    conda activate geo
    python scripts\\heat_analysis\\01_download_era5_utci.py --test
"""
import argparse
import time
import calendar
from pathlib import Path
import cdsapi

# Import from config.py in same folder
from config import DATA_RAW, BBOX, YEARS

def download_month(year, month, max_retries=3):
    """Download UTCI for one month with retry logic."""
    
    # Create year directory
    year_dir = DATA_RAW / f"era5_utci_{year}"
    year_dir.mkdir(parents=True, exist_ok=True)
    
    month_file = year_dir / f"era5_utci_{year}_{month:02d}.nc"
    
    if month_file.exists():
        size_mb = month_file.stat().st_size / 1024 / 1024
        print(f"  ✓ {year}-{month:02d} already exists ({size_mb:.1f} MB), skipping")
        return True
    
    client = cdsapi.Client()
    dataset = "derived-utci-historical"
    
    # Get correct number of days for this month
    _, num_days = calendar.monthrange(year, month)
    
    for attempt in range(max_retries):
        try:
            print(f"  Downloading {year}-{month:02d} (attempt {attempt + 1}/{max_retries})...", end='', flush=True)
            
            # Use EXACT format from CDS web form
            request = {
                "variable": ["universal_thermal_climate_index"],
                "version": "1_1",  # KEY: This was missing!
                "product_type": "consolidated_dataset",
                "year": [str(year)],
                "month": [f"{month:02d}"],
                "day": [f"{d:02d}" for d in range(1, num_days + 1)],
                "area": [BBOX['north'], BBOX['west'], BBOX['south'], BBOX['east']]
            }
            
            # Download using the .download() method
            client.retrieve(dataset, request).download(str(month_file))
            
            size_mb = month_file.stat().st_size / 1024 / 1024
            print(f" ✓ {size_mb:.1f} MB")
            return True
            
        except Exception as e:
            print(f" ✗")
            error_msg = str(e)
            print(f"    Error: {error_msg[:200]}")
            
            if attempt < max_retries - 1:
                wait = 30 * (attempt + 1)
                print(f"    Waiting {wait}s before retry...")
                time.sleep(wait)
    
    print(f"  ✗ Failed to download {year}-{month:02d} after {max_retries} attempts")
    return False


def download_year(year):
    """Download all months for one year."""
    
    print(f"\nDownloading {year}...")
    
    successful_months = []
    failed_months = []
    
    for month in range(1, 13):
        if download_month(year, month):
            successful_months.append(month)
        else:
            failed_months.append(month)
    
    if failed_months:
        print(f"\n✗ {year} incomplete: Failed months {[f'{m:02d}' for m in failed_months]}")
        return False
    else:
        print(f"\n✓ {year} complete: {len(successful_months)}/12 months")
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', 
                       help='Download 2020-2024 only (test mode)')
    parser.add_argument('--start', type=int, help='Start year')
    parser.add_argument('--end', type=int, help='End year')
    parser.add_argument('--year', type=int, help='Download single year')
    parser.add_argument('--all', action='store_true', 
                       help='Download 1979-2025')
    
    args = parser.parse_args()
    
    # Determine years to download
    if args.test:
        years = list(range(2020, 2025))
        print("\n" + "="*60)
        print("TEST MODE: Downloading 2020-2024")
        print("="*60)
        print("Strategy: Month-by-month (version 1.1)")
        print("Size: ~15 GB total (12 files per year)")
        print("Time: ~4-6 hours total")
        print("="*60)
    elif args.year:
        years = [args.year]
        print(f"\nDownloading single year: {args.year}")
    elif args.start and args.end:
        years = list(range(args.start, args.end + 1))
    elif args.all:
        years = YEARS
        print(f"\nFULL MODE: Downloading 1979-2025 (~140 GB, ~2-3 days)")
    else:
        parser.error("Specify --test, --year, --start/--end, or --all")
    
    print(f"\nTarget: {len(years)} years")
    print(f"Output: {DATA_RAW}")
    print(f"Bbox: {BBOX}")
    print(f"Version: 1.1 (consolidated dataset)")
    
    # Download
    successful = []
    failed = []
    
    start_time = time.time()
    
    for i, year in enumerate(years):
        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(years)}] YEAR {year}")
        print(f"{'='*60}")
        
        if download_year(year):
            successful.append(year)
        else:
            failed.append(year)
    
    # Summary
    elapsed = (time.time() - start_time) / 3600  # hours
    print(f"\n\n{'='*60}")
    print(f"DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"Successful: {len(successful)}/{len(years)} years")
    print(f"Time: {elapsed:.1f} hours")
    
    if successful:
        print(f"\nCompleted years: {successful}")
    
    if failed:
        print(f"\nFailed years: {failed}")
        print(f"\nTo retry failed years:")
        for year in failed:
            print(f"  python scripts\\heat_analysis\\01_download_era5_utci.py --year {year}")
    
    print(f"{'='*60}")
    
    # Next steps
    if successful and not failed:
        print("\n✓ All downloads complete!")
        print("\nNext step:")
        print("  python scripts\\heat_analysis\\02_precompute_annual_metrics.py --test")
    elif successful:
        print("\n⚠ Partial success - some years failed")
        print("  You can proceed with successful years or retry failed ones")

if __name__ == "__main__":
    main()