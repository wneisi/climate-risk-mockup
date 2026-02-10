
# Common configuration for all hazards

from pathlib import Path

# Repository root
REPO_ROOT = Path(__file__).parent.parent

# Shared settings
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

# Projection years
PROJECTION_YEARS = [2030, 2040, 2050]

# Return periods for analysis
RETURN_PERIODS = [10, 25, 50]

# Paths
DATA_ROOT = REPO_ROOT / "data"
MAPS_ROOT = REPO_ROOT / "maps"
DOCS_ROOT = REPO_ROOT / "docs"

# Boundaries (shared across all hazards)
BOUNDARIES_DIR = DATA_ROOT / "boundaries"
