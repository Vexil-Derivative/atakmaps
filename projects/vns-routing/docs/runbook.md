# VNS Routing Runbook (Offline GHZ + MVUM/USFS)

Offline-focused guide for building GraphHopper GHZ packages for ATAK VNS. OSRM/service steps remain optional.

## Dependencies
- Docker + Docker Compose
- Python 3 (host) for packaging GHZ
- Java only needed if you run GraphHopper outside Docker
- (Optional) GDAL/OGR if you want to generate MVUM overlays from shapefiles locally

## Prep environment
1) `cp .env.template .env` and set values (region name, paths, ports).
2) Place `<region>.osm.pbf` (plus `.poly`/`.timestamp`) in `projects/vns-routing/data/osm/`.
3) Ensure MVUM shapefiles are available (defaults point to `projects/mvum/inputs/`).

## Build GraphHopper GHZ (offline routing)
1) `scripts/prep_gh.sh` (default image: israelhikingmap/graphhopper:latest; override with GH_IMAGE)
   - Copies the PBF/custom model into `data/osm/<region>/` and runs import.
   - Packages `graph-cache` + `.poly` + `.timestamp` + `gh-mvum.json` into `<region>.ghz`.
2) GHZ lives alongside the OSRM data in `data/osm/<region>/`.

## MVUM weighting
- GraphHopper: `profiles/gh-mvum.json` reduces speed/priority on track/unpaved segments. Extend it with custom encoded values if you add MVUM ids to OSM data.
- (Optional) OSRM: `profiles/car.lua` and `mvum_speed_overrides.csv` remain if you ever need an online service. Generate the CSV by intersecting MVUM roads with OSM way ids (see `scripts/mvum_overlay.py` placeholder).

## Optional services (if needed later)
- Prep OSRM: `scripts/prep_osrm.sh` (osrm/osrm-backend:v5.27.0)
- Start: `docker compose --env-file .env -f docker/docker-compose.yml up -d`
- Stop:  `docker compose --env-file .env -f docker/docker-compose.yml down`
- OSRM listens on `${OSRM_PORT}`; GHZ file server on `${GH_FILESERVER_PORT}`.

## Adding regions / refreshing data
1) Drop new PBF/poly/timestamp.
2) Re-run `prep_osrm.sh` and `prep_gh.sh` (they overwrite outputs).
3) Keep MVUM overrides in sync if road designations change.

## Future extensions
- Add a compose overlay for OAuth/AD auth and TLS (see reference doc for systemd service wiring).
- Automate MVUM overlay generation (OGR or osmnx) to emit `mvum_speed_overrides.csv`.
- Add health checks/metrics exporters for OSRM and the file server.
