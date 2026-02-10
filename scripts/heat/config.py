"""
Central configuration for climate risk analysis.
User can edit thresholds here.
"""
from pathlib import Path

# Paths (Windows-compatible)
REPO_ROOT = Path(r"C:\Users\wneis\Documents\GitHub\climate-risk-mockup")
DATA_RAW = REPO_ROOT / "data" / "raw" / "utci"
DATA_INTERMEDIATE = REPO_ROOT / "data" / "intermediate"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
MAPS_DIR = REPO_ROOT / "maps"

# Create directories if they don't exist
DATA_INTERMEDIATE.mkdir(parents=True, exist_ok=True)

# Spatial extent (Iberian Peninsula)
BBOX = {
    'north': 44.0,
    'south': 36.0,
    'west': -10.0,
    'east': 5.0
}

# Temporal extent
YEAR_START = 1979
YEAR_END = 2025
YEARS = list(range(YEAR_START, YEAR_END + 1))

# === USER-CONFIGURABLE HEAT THRESHOLDS ===
# These can be changed without modifying other code
HEAT_THRESHOLDS = {
    'moderate': 32.0,     # Strong heat stress (UTCI 32-40°C)
    'extreme': 40.0,      # Very strong heat stress (UTCI ≥40°C)
}

# Projection years
PROJECTION_YEARS = [2030, 2040, 2050]

# Return periods for analysis
RETURN_PERIODS = [10, 25, 50]

print(f"✓ Config loaded: Thresholds = {HEAT_THRESHOLDS}")