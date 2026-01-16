#!/usr/bin/env python3
"""
Placeholder helper to intersect MVUM roads with OSM ways and emit per-way speed caps.

Suggested approach:
1) Convert MVUM roads to GeoJSON/GeoPackage with OSM-friendly CRS (EPSG:4326).
2) Export OSM ways (lines) with ids using `osmium tags-filter` or `osmnx`.
3) Spatially join MVUM -> OSM to find overlapping segments and decide caps (e.g., 25 kph for primitive roads, 40 kph for maintained gravel).
4) Write `mvum_speed_overrides.csv` with rows `osm_id,speed_kph` for the OSRM profile.

This stub remains so the pipeline has a reserved entry point; swap in your preferred geoprocessing stack (Fiona/Shapely/GeoPandas/GDAL).
"""

from pathlib import Path
import sys


def main() -> int:
    print("mvum_overlay.py is a placeholder; replace with your MVUM->OSM join logic.")
    print("Expected output: profiles/mvum_speed_overrides.csv (osm_id,speed_kph)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
