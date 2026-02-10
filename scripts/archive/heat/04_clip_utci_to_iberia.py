from pathlib import Path
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds

# Repo paths
REPO = Path(__file__).resolve().parents[1]
IN_TIF = REPO / "data" / "processed" / "utci_20200101_era5_0p25deg_epsg4326.tif"
OUT_TIF = REPO / "data" / "processed" / "utci_20200101_iberia_epsg4326.tif"

# Iberian Peninsula bounding box (lon/lat, EPSG:4326)
# (W, S, E, N)
IBERIA_BOUNDS_4326 = (-10.0, 35.5, 4.8, 44.6)

def main():
    if not IN_TIF.exists():
        raise FileNotFoundError(f"Input not found: {IN_TIF}")

    with rasterio.open(IN_TIF) as src:
        # Ensure bounds are in the raster CRS
        if src.crs and src.crs.to_string() != "EPSG:4326":
            w, s, e, n = transform_bounds("EPSG:4326", src.crs, *IBERIA_BOUNDS_4326)
        else:
            w, s, e, n = IBERIA_BOUNDS_4326

        # Build a window and clip it to dataset extent
        window = from_bounds(w, s, e, n, transform=src.transform)
        window = window.round_offsets().round_lengths()

        # Read data in the window
        data = src.read(1, window=window)

        # Compute output transform
        out_transform = src.window_transform(window)

        meta = src.meta.copy()
        meta.update(
            {
                "height": data.shape[0],
                "width": data.shape[1],
                "transform": out_transform,
                "compress": "deflate",
            }
        )

        OUT_TIF.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(OUT_TIF, "w", **meta) as dst:
            dst.write(data, 1)

    print("Wrote:", OUT_TIF)

if __name__ == "__main__":
    main()
