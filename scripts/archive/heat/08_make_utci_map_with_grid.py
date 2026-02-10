from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
import folium
from folium.raster_layers import ImageOverlay
import branca.colormap as cm

# --- Paths ---
REPO = Path(__file__).resolve().parents[1]
TIF = REPO / "data" / "processed" / "utci_20200101_iberia_celsius_epsg4326.tif"  # adjust if needed
OUT_HTML = REPO / "maps" / "utci_20200101_iberia_celsius_coloured_hover.html"

# --- Fixed scale (°C) ---
VMIN, VMAX = -10.0, 40.0  # keep fixed to compare across days

# --- Grid sampling for hover layer (bigger = fewer cells = faster) ---
STEP = 6  # 4=denser, 10=lighter

# --- Colormap for legend (fixed °C scale) ---
colormap = cm.LinearColormap(
    colors=["#2c105c", "#1f77b4", "#22c55e", "#eab308", "#f97316", "#dc2626"],
    vmin=VMIN,
    vmax=VMAX,
)
colormap.caption = "UTCI (°C) — fixed scale"

# --- Colormap for image (normalized 0..1) ---
# IMPORTANT: this fixes the “single colour blob” problem
colormap_norm = cm.LinearColormap(
    colors=colormap.colors,
    vmin=0.0,
    vmax=1.0,
)

def clamp01(x):
    return np.clip(x, 0.0, 1.0)

def rgba_from_values(arr, vmin, vmax):
    """
    Convert a 2D float array into an RGBA uint8 image using branca colormap.
    Transparent where NaN.
    """
    rgba = np.zeros((arr.shape[0], arr.shape[1], 4), dtype=np.uint8)

    mask = np.isfinite(arr)
    if not np.any(mask):
        return rgba

    # Normalize to 0..1
    norm = (arr - vmin) / (vmax - vmin)
    norm = clamp01(norm)

    flat = norm[mask].ravel()
    # Use the NORMALIZED colormap (0..1)
    hex_colors = [colormap_norm(x) for x in flat]

    def hex_to_rgba(h):
        h = h.lstrip("#")
        if len(h) == 6:
            r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16); a = 255
        elif len(h) == 8:
            r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16); a = int(h[6:8], 16)
        else:
            r, g, b, a = 0, 0, 0, 0
        return r, g, b, a

    rgba_vals = np.array([hex_to_rgba(h) for h in hex_colors], dtype=np.uint8)
    rgba[mask] = rgba_vals
    rgba[~mask, 3] = 0  # transparent alpha for nodata/NaN
    return rgba

# --- Read raster ---
with rasterio.open(TIF) as src:
    arr = src.read(1).astype("float32")
    bounds = src.bounds
    crs = src.crs
    transform = src.transform
    nodata = src.nodata

# Handle nodata
if nodata is not None:
    arr = np.where(arr == nodata, np.nan, arr)

# If it looks like Kelvin, convert to Celsius
finite = arr[np.isfinite(arr)]
if finite.size > 0 and np.nanmean(finite) > 100:
    arr = arr - 273.15

# Quick sanity stats (helps debug “blob” vs real data)
if np.isfinite(arr).any():
    print(
        "UTCI °C stats:",
        float(np.nanmin(arr)),
        float(np.nanpercentile(arr, 5)),
        float(np.nanpercentile(arr, 50)),
        float(np.nanpercentile(arr, 95)),
        float(np.nanmax(arr)),
    )
else:
    print("WARNING: raster contains no finite values after nodata handling.")

# --- Build coloured RGBA overlay ---
rgba_img = rgba_from_values(arr, VMIN, VMAX)

# Folium bounds must be lat/lon
if crs and crs.to_string() != "EPSG:4326":
    left, bottom, right, top = transform_bounds(
        crs, "EPSG:4326",
        bounds.left, bounds.bottom, bounds.right, bounds.top
    )
else:
    left, bottom, right, top = bounds.left, bounds.bottom, bounds.right, bounds.top

m = folium.Map(
    location=[(bottom + top) / 2, (left + right) / 2],
    zoom_start=5,
    tiles="CartoDB positron",
)

# Put raster in its own pane so it sits nicely
folium.map.CustomPane("utci_raster", z_index=350).add_to(m)

ImageOverlay(
    image=rgba_img,
    bounds=[[bottom, left], [top, right]],
    opacity=0.75,
    name="UTCI raster (°C, coloured)",
    interactive=False,
    cross_origin=False,
    zindex=350,
).add_to(m)

# --- Transparent hover grid (interactive, but invisible) ---
features = []
h, w = arr.shape

def pixel_to_lonlat(r, c):
    x, y = rasterio.transform.xy(transform, r, c, offset="center")
    return (x, y)  # lon, lat for EPSG:4326

# If your processed tif is not EPSG:4326, stop early with a clear message.
if crs is None or crs.to_string() != "EPSG:4326":
    raise RuntimeError(
        f"Expected {TIF.name} to be EPSG:4326 for hover grid, but got {crs}. "
        "Reproject to EPSG:4326 first."
    )

for r in range(0, h - STEP, STEP):
    for c in range(0, w - STEP, STEP):
        rr = r + STEP // 2
        cc = c + STEP // 2
        v = arr[rr, cc]
        if not np.isfinite(v):
            continue

        lon1, lat1 = pixel_to_lonlat(r, c)
        lon2, lat2 = pixel_to_lonlat(r, c + STEP)
        lon3, lat3 = pixel_to_lonlat(r + STEP, c + STEP)
        lon4, lat4 = pixel_to_lonlat(r + STEP, c)

        poly = [
            [lat1, lon1],
            [lat2, lon2],
            [lat3, lon3],
            [lat4, lon4],
            [lat1, lon1],
        ]

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[ [p[1], p[0]] for p in poly ]]  # GeoJSON uses [lon,lat]
            },
            "properties": {"utci_c": float(v)},
        })

grid_layer = folium.GeoJson(
    {"type": "FeatureCollection", "features": features},
    name="UTCI sampled grid (hover/click)",
    style_function=lambda feat: {
        # Fully invisible, but still interactive
        "color": "#000000",
        "weight": 0,
        "opacity": 0.0,
        "fillColor": "#000000",
        "fillOpacity": 0.0,
    },
    highlight_function=lambda feat: {
        # Subtle outline only while hovering
        "weight": 1,
        "opacity": 0.25,
        "color": "#ffffff",
        "fillOpacity": 0.0,
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["utci_c"],
        aliases=["UTCI (°C):"],
        localize=True,
        sticky=True,
        labels=True,
        style=(
            "background-color: rgba(0,0,0,0.65); color: white; "
            "border: 0px; border-radius: 4px; box-shadow: none; "
            "font-size: 12px; padding: 6px;"
        ),
    ),
)
grid_layer.add_to(m)

# Legend / colourbar (fixed °C scale)
colormap.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
m.save(str(OUT_HTML))
print("Wrote:", OUT_HTML)
