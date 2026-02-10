from pathlib import Path
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import rasterio
from pyproj import Transformer


# Iberian Peninsula bounds (WGS84)
WEST, SOUTH, EAST, NORTH = -9.5, 36.0, 3.5, 43.8

# Grid spacing in meters (start safe for performance)
GRID_SPACING_M = 10_000  # 10 km


def main():
    repo = Path(__file__).resolve().parents[1]

    tif = repo / "data" / "processed" / "utci_20200101_iberia_celsius_epsg4326.tif"
    out_geojson = repo / "data" / "processed" / "utci_20200101_iberia_grid_10km.geojson"

    if not tif.exists():
        raise FileNotFoundError(f"Missing GeoTIFF: {tif}")

    # Transform bounds from EPSG:4326 -> EPSG:3857 (meters) to build an evenly spaced grid
    to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    to_4326 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    minx, miny = to_3857.transform(WEST, SOUTH)
    maxx, maxy = to_3857.transform(EAST, NORTH)

    xs = np.arange(minx, maxx, GRID_SPACING_M)
    ys = np.arange(miny, maxy, GRID_SPACING_M)

    # Create grid points in 4326
    points_lonlat = []
    for y in ys:
        for x in xs:
            lon, lat = to_4326.transform(x, y)
            points_lonlat.append((lon, lat))

    print(f"Grid points: {len(points_lonlat):,}")

    # Sample raster at point locations
    with rasterio.open(tif) as src:
        nodata = src.nodata

        # rasterio.sample expects (x, y) = (lon, lat) for EPSG:4326 rasters
        samples = list(src.sample(points_lonlat))
        vals = np.array([s[0] for s in samples], dtype="float32")

    # Filter nodata / invalid
    if nodata is not None:
        mask_valid = np.isfinite(vals) & (vals != nodata)
    else:
        mask_valid = np.isfinite(vals)

    kept = int(mask_valid.sum())
    print(f"Valid samples kept: {kept:,}")

    # Build GeoDataFrame
    lons = np.array([p[0] for p in points_lonlat], dtype="float64")[mask_valid]
    lats = np.array([p[1] for p in points_lonlat], dtype="float64")[mask_valid]
    vals = vals[mask_valid]

    gdf = gpd.GeoDataFrame(
        {
            "utci_c": vals.round(2),
            "lon": lons.round(6),
            "lat": lats.round(6),
        },
        geometry=[Point(xy) for xy in zip(lons, lats)],
        crs="EPSG:4326",
    )

    out_geojson.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(out_geojson, driver="GeoJSON")
    print("Wrote:", out_geojson)


if __name__ == "__main__":
    main()
