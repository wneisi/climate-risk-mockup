"""
Download municipality boundaries for Spain and Portugal.

Uses GADM (Global Administrative Areas) - reliable, free source.

Usage:
    python scripts\\heat_analysis\\07_download_boundaries.py
"""
import requests
import json
from pathlib import Path

from config import DATA_RAW

print("="*60)
print("DOWNLOADING MUNICIPALITY BOUNDARIES")
print("="*60)
print("\nUsing GADM (Global Administrative Areas Database)")
print("License: Free for non-commercial use")
print("="*60)

boundaries_dir = DATA_RAW / "boundaries"
boundaries_dir.mkdir(parents=True, exist_ok=True)

def download_file(url, filename, description):
    """Download a file with progress."""
    print(f"\n{description}")
    print(f"  URL: {url}")
    print(f"  Downloading...", end='', flush=True)
    
    try:
        response = requests.get(url, timeout=120, stream=True)
        
        if response.status_code == 200:
            filepath = boundaries_dir / filename
            
            # Get file size
            total_size = int(response.headers.get('content-length', 0))
            
            with open(filepath, 'wb') as f:
                if total_size == 0:
                    f.write(response.content)
                else:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if downloaded % (1024 * 1024) == 0:  # Every MB
                            print(".", end='', flush=True)
            
            size_mb = filepath.stat().st_size / 1024 / 1024
            print(f" ✓")
            print(f"  Saved: {filepath}")
            print(f"  Size: {size_mb:.1f} MB")
            return True
        else:
            print(f" ✗ Failed (Status {response.status_code})")
            return False
            
    except Exception as e:
        print(f" ✗ Error: {e}")
        return False

# Spain - Level 4 (Municipalities)
spain_success = download_file(
    url="https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_ESP_4.json",
    filename="spain_municipalities.geojson",
    description="1. Spanish Municipalities (Level 4 - ~8,100 municipios)"
)

# Portugal - Level 2 (Municipalities/Concelhos)
portugal_success = download_file(
    url="https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_PRT_2.json",  
    filename="portugal_municipalities.geojson",
    description="2. Portuguese Municipalities (Level 2 - 308 concelhos)"
)

print(f"\n{'='*60}")
print("DOWNLOAD SUMMARY")
print(f"{'='*60}")

if spain_success and portugal_success:
    print("✓ All downloads successful!")
    print("\nNext step:")
    print("  python scripts\\heat_analysis\\08_create_choropleth_map.py")
else:
    print("⚠ Some downloads failed")
    
    if not spain_success:
        print("\nSpain alternative:")
        print("  Manual download from: https://gadm.org/download_country.html")
        print("  Country: Spain, Level: 4, Format: GeoJSON")
        
    if not portugal_success:
        print("\nPortugal alternative:")
        print("  Manual download from: https://gadm.org/download_country.html")
        print("  Country: Portugal, Level: 2, Format: GeoJSON")
    
    print("\nSave files to:")
    print(f"  {boundaries_dir}")

print(f"{'='*60}")