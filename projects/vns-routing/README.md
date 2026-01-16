# VNS Routing (Offline GHZ + MVUM/USFS)

Offline-focused pipeline to prep GraphHopper GHZ packages for the ATAK VNS plugin using OSM as the base, with MVUM/USFS overlays to slow/penalize forest roads. OSRM service files remain optional; the default flow only builds the offline GHZ.

## Layout
- `docker/` — Optional compose stack if you later want a live OSRM service.
- `profiles/` — OSRM profile (`car.lua`) and GraphHopper custom model for MVUM-aware speeds.
- `scripts/` — Data prep scripts: GraphHopper GHZ build (offline), optional OSRM prep, MVUM overlay utilities.
- `data/osm/` — Drop `<region>.osm.pbf`, `<region>.poly`, `<region>.timestamp` here; outputs land under `data/osm/<region>/`.
- `data/usfs/` — MVUM/TrailNFS shapefiles/FGDB for overlays.
- `.env.template` — runtime variables for Compose and scripts.
- `docs/runbook.md` — operations guide (mirrors the reference doc with local tweaks).

## Quick start (offline GHZ)
1) Copy `.env.template` to `.env` and set `OSRM_REGION`, `OSRM_PBF`, `GH_DATA_ROOT`, `MVUM_ROADS`, `MVUM_TRAILS` paths.
2) Place the PBF/poly/timestamp for your region in `data/osm/` (e.g., `data/osm/nebraska.osm.pbf`).
3) Prep GraphHopper GHZ (offline): `scripts/prep_gh.sh` (runs graphhopper 1.0 in Docker with the MVUM-aware custom model) — outputs `<region>.ghz` in `data/osm/<region>/`.
4) (Optional) Prep OSRM data for live routing: `scripts/prep_osrm.sh`.
5) (Optional) Start services if you later need them: `docker compose --env-file .env -f docker/docker-compose.yml up -d`.

## MVUM weighting
- GraphHopper uses `profiles/gh-mvum.json` custom model to reduce `speed_factor`/`priority` for MVUM-tagged segments and unpaved surfaces.
- OSRM bits are retained only if you want an online service later; otherwise ignore `car.lua`.
- A placeholder overlay helper `scripts/mvum_overlay.py` is included to intersect MVUM geometries with OSM ways and emit per-way caps.

## Notes
- Compose defaults to published images (`israelhikingmap/graphhopper:latest` for GH import, plus OSRM/python images if you enable services). Swap tags in `docker/docker-compose.yml` as desired.
- Keep data on a fast disk; GraphHopper import can need RAM/CPU for large regions.
- The MVUM and USFS non-motorized exports already live in `projects/mvum` and `projects/usfs`; reuse those inputs for overlays here.
