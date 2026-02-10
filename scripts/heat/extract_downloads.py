"""
Extract ZIP files downloaded from CDS API.

The .nc files are actually ZIP archives containing the real NetCDF files.

Usage:
    python scripts\\heat_analysis\\extract_downloads.py
"""
import zipfile
from pathlib import Path
from config import DATA_RAW, YEARS

def extract_month(zip_file):
    """Extract a single ZIP file."""
    
    print(f"  Extracting {zip_file.name}...", end='', flush=True)
    
    try:
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            # Extract to same directory
            zip_ref.extractall(zip_file.parent)
        
        # Get the extracted file name
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            extracted_files = zip_ref.namelist()
        
        print(f" ✓ (extracted {len(extracted_files)} file(s))")
        
        # Optionally delete the ZIP after extraction
        # zip_file.unlink()
        
        return True
        
    except Exception as e:
        print(f" ✗ Error: {e}")
        return False

def extract_year(year):
    """Extract all months for one year."""
    
    year_dir = DATA_RAW / f"era5_utci_{year}"
    
    if not year_dir.exists():
        print(f"⚠ Year folder not found: {year}")
        return False
    
    print(f"\nExtracting {year}...")
    
    # Find all .nc files (which are actually ZIPs)
    nc_files = list(year_dir.glob("*.nc"))
    
    if not nc_files:
        print(f"  No .nc files found")
        return False
    
    print(f"  Found {len(nc_files)} files")
    
    successful = 0
    for nc_file in nc_files:
        if extract_month(nc_file):
            successful += 1
    
    print(f"  ✓ Extracted {successful}/{len(nc_files)} files")
    
    return successful == len(nc_files)

def main():
    print("="*60)
    print("EXTRACTING CDS DOWNLOADS")
    print("="*60)
    print("The downloaded .nc files are ZIP archives.")
    print("Extracting to get the actual NetCDF data...")
    print("="*60)
    
    # Process test years (2020-2024)
    test_years = list(range(2020, 2025))
    
    successful = []
    failed = []
    
    for year in test_years:
        if extract_year(year):
            successful.append(year)
        else:
            failed.append(year)
    
    print("\n" + "="*60)
    print("EXTRACTION COMPLETE")
    print("="*60)
    print(f"Successful: {len(successful)}/{len(test_years)} years")
    
    if failed:
        print(f"Failed: {failed}")
    
    print("\nNext step:")
    print("  python scripts\\heat_analysis\\02_precompute_annual_metrics.py --test")
    print("="*60)

if __name__ == "__main__":
    main()