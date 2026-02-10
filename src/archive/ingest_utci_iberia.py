import cdsapi
from pathlib import Path

# Define paths
PROJECT_ROOT = Path(r"C:\Users\wneis\Documents\GitHub\climate-risk-mockup")
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"

# Define the request for the Iberian Peninsula
dataset = "derived-utci-historical"
request = {
    "variable": ["universal_thermal_climate_index"],
    "version": "1_1",
    "year": ["2020", "2021", "2022"],
    "month": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"],
    "day": ["01", "15"],
    "area": [43.8, -9.5, 36.0, 3.5],  # North, West, South, East
    "format": "netcdf"
}

# Initialize the CDS API client
client = cdsapi.Client()

# Download the data
output_path = DATA_INTERIM / "utci_iberian_peninsula.nc"
client.retrieve(dataset, request, output_path)
print(f"Data downloaded to: {output_path}")
