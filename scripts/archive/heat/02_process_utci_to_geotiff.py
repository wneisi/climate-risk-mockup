from pathlib import Path
import numpy as np
import xarray as xr
import rioxarray  # noqa: F401
import matplotlib.pyplot as plt

# --- paths ---
REPO = Path(__file__).resolve().parents[1]
NC_PATH = REPO / "data" / "raw" / "ECMWF_utci_20200101_v1.1_con.nc"
OUT_TIF = REPO / "data" / "processed" / "utci_20200101_era5_0p25deg_epsg4326.tif"

# --- load ---
ds = xr.open_dataset(NC_PATH, engine="netcdf4")
print(ds)
print("Data variables:", list(ds.data_vars))

# --- pick variable (prefer 'utci' if present) ---
if "utci" in ds.data_vars:
    da = ds["utci"]
else:
    # fallback: first data var
    da = ds[list(ds.data_vars)[0]]
print("Using variable:", da.name)
print("Dims:", da.dims)

# --- drop time dimension if present ---
for tdim in ["time", "valid_time"]:
    if tdim in da.dims:
        da = da.isel({tdim: 0})

# --- normalize coordinate names to lat/lon if needed ---
# Many CDS products use 'latitude'/'longitude'
rename = {}
if "latitude" in da.coords: rename["latitude"] = "lat"
if "longitude" in da.coords: rename["longitude"] = "lon"
if rename:
    da = da.rename(rename)

# --- ensure we have lat/lon ---
if not ("lat" in da.coords and "lon" in da.coords):
    raise ValueError(f"Expected lat/lon coords but found coords={list(da.coords)} dims={da.dims}")

# --- quick sanity plot (map-like) ---
plt.figure()
da.plot()
plt.title(f"{da.name} (quick plot)")
plt.tight_layout()
plt.show()

# --- write GeoTIFF ---
# Assign CRS WGS84 and export
da = da.rio.write_crs("EPSG:4326", inplace=False)

# rioxarray expects spatial dims named x/y; set them from lon/lat
da = da.rio.set_spatial_dims(x_dim="lon", y_dim="lat", inplace=False)

# CDS lat often descending; GeoTIFF prefers top-to-bottom layout; rioxarray handles it, but we ensure consistent orientation
# (No manual flip unless we see it exported upside down.)
OUT_TIF.parent.mkdir(parents=True, exist_ok=True)
da.rio.to_raster(OUT_TIF)
print("Wrote:", OUT_TIF)

