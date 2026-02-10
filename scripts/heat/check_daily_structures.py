"""
Check structure of daily NetCDF files.
"""
import xarray as xr
from pathlib import Path

# Check one daily file
test_file = Path("data/raw/utci/era5_utci_2020/ECMWF_utci_20200101_v1.1_con.area-subset.44.0.5.0.36.0.-10.0.nc")

print("="*60)
print("CHECKING DAILY FILE STRUCTURE")
print("="*60)
print(f"\nFile: {test_file.name}")

if not test_file.exists():
    print("File not found!")
    # Try to find any file
    year_dir = Path("data/raw/utci/era5_utci_2020")
    files = list(year_dir.glob("ECMWF*.nc"))
    if files:
        test_file = files[0]
        print(f"Using instead: {test_file.name}")
    else:
        print("No files found!")
        exit(1)

print(f"\nOpening file...")
ds = xr.open_dataset(test_file, engine='netcdf4')

print(f"\nDimensions:")
for dim, size in ds.dims.items():
    print(f"  {dim}: {size}")

print(f"\nVariables:")
for var in ds.variables:
    print(f"  {var}: {ds[var].dims}, shape={ds[var].shape}")

print(f"\nCoordinates:")
print(f"  time: {ds['time'].values if 'time' in ds else 'N/A'}")
print(f"  lat: min={ds['latitude'].min().values:.2f}, max={ds['latitude'].max().values:.2f}")
print(f"  lon: min={ds['longitude'].min().values:.2f}, max={ds['longitude'].max().values:.2f}")

# Find UTCI variable
utci_vars = ['utci', 'Universal thermal climate index', 'var260015']
utci_var = None
for v in utci_vars:
    if v in ds.variables:
        utci_var = v
        break

if utci_var:
    print(f"\nUTCI variable: '{utci_var}'")
    print(f"  Shape: {ds[utci_var].shape}")
    print(f"  Dims: {ds[utci_var].dims}")
    print(f"  Sample values: {ds[utci_var].values.flatten()[:5]}")
else:
    print("\n⚠ UTCI variable not found!")

print(f"\n{'='*60}")
print("EXPECTED:")
print("  - time dimension should have size 1 (one day)")
print("  - OR no time dimension (just lat/lon)")
print("  - lat/lon should be grid (e.g., 33x61)")
print("="*60)

ds.close()