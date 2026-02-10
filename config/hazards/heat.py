# Heat hazard-specific configuration

from pathlib import Path
from config.common import DATA_ROOT, MAPS_ROOT

# Heat data paths
HEAT_DATA = DATA_ROOT / "heat"
HEAT_RAW = HEAT_DATA / "raw"
HEAT_PROCESSED = HEAT_DATA / "processed"
HEAT_MAPS = MAPS_ROOT / "heat"

# Create directories
HEAT_RAW.mkdir(parents=True, exist_ok=True)
HEAT_PROCESSED.mkdir(parents=True, exist_ok=True)
HEAT_MAPS.mkdir(parents=True, exist_ok=True)

# Heat thresholds (user-configurable)
HEAT_THRESHOLDS = {
    'moderate': 32.0,     # Strong heat stress (UTCI 32-40C)
    'extreme': 40.0,      # Very strong heat stress (UTCI >= 40C)
}

print(f"Heat config loaded: Thresholds = {HEAT_THRESHOLDS}")