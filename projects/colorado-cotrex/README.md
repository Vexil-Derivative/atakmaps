# Colorado COTREX → ATAK

Exports Colorado’s COTREX trail network and trailheads to ATAK-ready KMZs with per-use colorization and optional per-use splits.

## Source data
- Download (large ~750 MB ZIP): https://www.arcgis.com/sharing/rest/content/items/cae8ed959b8a4ed48680df62b31eec60/data (CPW_Trails.zip)
- Extract into `projects/colorado-cotrex/inputs/` so these files sit together:
  - `COTREX_Trails.shp` (+ .dbf/.shx/.prj/.cpg/.xml)
  - `COTREX_Trailheads.shp` (+ sidecars)

## What gets generated
- `outputs/COTREX_Trails.kmz` — all COTREX trails, recolored by allowed uses, USFS-managed features filtered out (those are covered by MVUM/USFS projects).
- `outputs/COTREX_Trailheads.kmz` — trailheads with labeled icons.
- `outputs/COTREX_Trails_<category>.kmz` — per-use splits (Hiking, Horse, Bike, Motorcycle, ATV, OHV >50", Highway vehicles, Dogs) for selective loading.

## How to run
From repo root:
- `python3 projects/colorado-cotrex/main.py`

Requirements:
- Python 3 with GDAL/OGR and Python bindings available (`brew install gdal` on macOS).

## Notes
- USFS-managed features are intentionally filtered to avoid overlap with the MVUM/USFS exports.
- Styles use bright pink/orange hues per allowed use; labels come from `feature_id`/`name` fields.
- Trailhead KMZ includes icon tinting and descriptive tables for quick reference.
