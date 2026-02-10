from pathlib import Path
import numpy as np
import rasterio as rio

p = Path("data/interim/era5_heat_sample_corrected.tif")

with rio.open(p) as ds:
    a = ds.read(1)
    print("PATH:", p.resolve())
    print("CRS:", ds.crs)
    print("WIDTH/HEIGHT:", ds.width, ds.height)
    print("BANDS:", ds.count)
    print("DTYPE:", a.dtype)
    print("NODATA:", ds.nodata)
    print("MIN/MAX:", float(np.nanmin(a)), float(np.nanmax(a)))
