from pathlib import Path
import rasterio
import numpy as np

REPO = Path(__file__).resolve().parents[1]

IN_TIF = REPO / "data" / "processed" / "utci_20200101_iberia_epsg4326.tif"
OUT_TIF = REPO / "data" / "processed" / "utci_20200101_iberia_celsius_epsg4326.tif"

K_TO_C = 273.15

def main():
    if not IN_TIF.exists():
        raise FileNotFoundError(f"Missing input: {IN_TIF}")

    with rasterio.open(IN_TIF) as src:
        arr = src.read(1).astype("float32")
        meta = src.meta.copy()
        nodata = src.nodata

    # Respect nodata if present
    if nodata is not None:
        mask = arr == nodata
    else:
        mask = ~np.isfinite(arr)

    arr_c = arr - K_TO_C
    arr_c = arr_c.astype("float32")

    # Restore nodata
    if nodata is not None:
        arr_c[mask] = nodata
        meta.update(nodata=nodata)

    meta.update(dtype="float32", compress="deflate")

    OUT_TIF.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(OUT_TIF, "w", **meta) as dst:
        dst.write(arr_c, 1)

    # Print quick stats
    valid = np.isfinite(arr_c) if nodata is None else (arr_c != nodata)
    print("Wrote:", OUT_TIF)
    print("Min/Max (°C):", float(np.nanmin(arr_c[valid])), float(np.nanmax(arr_c[valid])))

if __name__ == "__main__":
    main()
