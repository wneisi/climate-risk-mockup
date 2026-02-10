from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
import folium
from folium.raster_layers import ImageOverlay


REPO = Path(__file__).resolve().parents[1]
TIF = REPO / "data" / "processed" / "utci_20200101_era5_0p25deg_epsg4326.tif"
OUT_HTML = REPO / "maps" / "utci_20200101.html"

if not TIF.exists():
    raise FileNotFoundError(f"GeoTIFF not found: {TIF}")

with rasterio.open(TIF) as ds:
    arr = ds.read(1).astype("float32")
    bounds = ds.bounds
    crs = ds.crs

# Normalize to 0..1 for display (robust to outliers)
mask = np.isfinite(arr)
if not np.any(mask):
    raise ValueError("Raster has no finite values to display.")

vmin, vmax = np.nanpercentile(arr[mask], [2, 98])
if vmax <= vmin:
    raise ValueError(f"Invalid vmin/vmax for normalization: vmin={vmin}, vmax={vmax}")

img = np.clip((arr - vmin) / (vmax - vmin), 0, 1)

# Folium wants bounds in lat/lon (EPSG:4326)
is_epsg4326 = crs is not None and (crs.to_epsg() == 4326)

if not is_epsg4326:
    left, bottom, right, top = transform_bounds(
        crs, "EPSG:4326",
        bounds.left, bounds.bottom, bounds.right, bounds.top
    )
else:
    left, bottom, right, top = bounds.left, bounds.bottom, bounds.right, bounds.top

m = folium.Map(
    location=[(bottom + top) / 2, (left + right) / 2],
    zoom_start=5,
    tiles="CartoDB positron"
)

overlay = ImageOverlay(
    image=img,
    bounds=[[bottom, left], [top, right]],
    opacity=0.7,
    name="UTCI (normalized 2–98%)"
)
overlay.add_to(m)
folium.LayerControl().add_to(m)

OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
m.save(str(OUT_HTML))
print("Wrote:", OUT_HTML)
