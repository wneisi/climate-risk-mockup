from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
import folium
from folium.raster_layers import ImageOverlay
from branca.colormap import LinearColormap
import matplotlib.cm as cm


REPO = Path(__file__).resolve().parents[1]
TIF = REPO / "data" / "processed" / "utci_20200101_iberia_celsius_epsg4326.tif"
OUT_HTML = REPO / "maps" / "utci_20200101_iberia_celsius_coloured.html"


if not TIF.exists():
    raise FileNotFoundError(f"GeoTIFF not found: {TIF}")

with rasterio.open(TIF) as src:
    arr = src.read(1).astype("float32")
    bounds = src.bounds
    crs = src.crs

mask = np.isfinite(arr)
if not np.any(mask):
    raise ValueError("Raster has no finite values to display.")

# Robust display range (avoids 1-2 extreme outliers ruining the scale)
vmin, vmax = np.nanpercentile(arr[mask], [2, 98])
if vmax <= vmin:
    raise ValueError(f"Invalid vmin/vmax: vmin={vmin}, vmax={vmax}")

# Normalize 0..1
norm = (arr - vmin) / (vmax - vmin)
norm = np.clip(norm, 0, 1)
norm[~mask] = 0  # placeholder; will be transparent via alpha below

# Create RGBA image using a matplotlib colormap
# Good default for heat stress: 'inferno' or 'plasma'
cmap = cm.get_cmap("coolwarm")
rgba = (cmap(norm) * 255).astype(np.uint8)  # (H, W, 4)

# Make NoData transparent
rgba[..., 3] = np.where(mask, 150, 0).astype(np.uint8)  # alpha channel

# Convert bounds to EPSG:4326 if needed
is_epsg4326 = crs is not None and (crs.to_epsg() == 4326)
if not is_epsg4326:
    left, bottom, right, top = transform_bounds(
        crs, "EPSG:4326", bounds.left, bounds.bottom, bounds.right, bounds.top
    )
else:
    left, bottom, right, top = bounds.left, bounds.bottom, bounds.right, bounds.top

# Base map
m = folium.Map(
    location=[(bottom + top) / 2, (left + right) / 2],
    zoom_start=6,
    tiles="CartoDB positron",
)

# Overlay (folium accepts numpy image arrays)
ImageOverlay(
    image=rgba,
    bounds=[[bottom, left], [top, right]],
    opacity=1.0,
    name="UTCI (°C)",
    interactive=True,
).add_to(m)

# Add legend / colour scale (in °C)
legend = LinearColormap(
    colors=["#313695", "#4575b4", "#74add1", "#abd9e9", "#e0f3f8", "#ffffbf", "#fee090", "#fdae61", "#f46d43", "#d73027", "#a50026"],
    #vmin=float(vmin),
    #vmax=float(vmax),
    vmin=-10,
    vmax=40,
    caption="UTCI (°C) — display range (2–98 percentile)",
)
legend.add_to(m)

folium.LayerControl().add_to(m)

# Add custom JavaScript to display raster value on click
click_js = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    var map = document.querySelector('.folium-map');
    map.onclick = function(e) {
        // Fetch the raster value at the clicked coordinates
        // For small datasets, you can embed the raster data as a JSON object in the HTML
        // and use JavaScript to look up the value at the clicked coordinates.
        // Example: alert("Value at (" + e.latlng.lat + ", " + e.latlng.lng + "): " + lookupValue(e.latlng.lat, e.latlng.lng));
        alert("Clicked at: Latitude " + e.latlng.lat.toFixed(4) + ", Longitude " + e.latlng.lng.toFixed(4));
    };
});
</script>
"""
m.get_root().html.add_child(folium.Element(click_js))

OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
m.save(str(OUT_HTML))
print("Wrote:", OUT_HTML)
print(f"Legend range: vmin={vmin:.2f} °C, vmax={vmax:.2f} °C")

