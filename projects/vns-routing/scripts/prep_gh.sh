#!/usr/bin/env bash
set -euo pipefail

# Build GraphHopper GHZ for offline VNS. Requires Docker (default image: israelhikingmap/graphhopper:latest).

ROOT_DIR=$(cd -- "$(dirname "$0")/.." && pwd)
REGION=${OSRM_REGION:-sample}
GH_IMAGE=${GH_IMAGE:-israelhikingmap/graphhopper:latest}
PBF_SRC=${OSRM_PBF:-"$ROOT_DIR/data/osm/${REGION}.osm.pbf"}
POLY_SRC=${OSRM_POLY:-"$ROOT_DIR/data/osm/${REGION}.poly"}
TS_SRC=${OSRM_TIMESTAMP:-"$ROOT_DIR/data/osm/${REGION}.timestamp"}
DATA_ROOT=${GH_DATA_ROOT:-"$ROOT_DIR/data/osm"}
CUSTOM_MODEL_SRC=${GH_CUSTOM_MODEL:-"$ROOT_DIR/profiles/gh-mvum.json"}

OUT_DIR="$(DATA_ROOT="$DATA_ROOT" REGION="$REGION" PYTHON_BIN="$(command -v python3 || command -v python)" sh -c '
if [ -z "$PYTHON_BIN" ]; then
  printf "ERROR: python3/python not found in PATH\n" >&2
  exit 1
fi
"$PYTHON_BIN" - <<PY
import os, sys
root = os.environ.get("DATA_ROOT", "")
region = os.environ.get("REGION", "sample")
base = os.path.join(root, region)
print(os.path.abspath(base))
PY
' )" || exit 1
mkdir -p "$OUT_DIR"

if [[ ! -f "$PBF_SRC" ]]; then
  echo "PBF not found: $PBF_SRC" >&2
  exit 2
fi
if [[ ! -f "$CUSTOM_MODEL_SRC" ]]; then
  echo "Custom model not found: $CUSTOM_MODEL_SRC" >&2
  exit 3
fi

copy_if_needed() {
  local src="$1" dest="$2"
  local src_abs dest_abs
  src_abs="$(cd -- "$(dirname "$src")" && pwd)/$(basename "$src")"
  dest_abs="$(cd -- "$(dirname "$dest")" && pwd)/$(basename "$dest")"
  if [[ "$src_abs" == "$dest_abs" ]]; then
    echo "Skipping copy (source == dest): $src_abs"
    return 0
  fi
  cp -f "$src" "$dest"
}

PBF_BASENAME="${REGION}.osm.pbf"
copy_if_needed "$PBF_SRC" "$OUT_DIR/$PBF_BASENAME"
copy_if_needed "$CUSTOM_MODEL_SRC" "$OUT_DIR/gh-mvum.json"
[[ -f "$POLY_SRC" ]] && copy_if_needed "$POLY_SRC" "$OUT_DIR/${REGION}.poly"
[[ -f "$TS_SRC" ]] && copy_if_needed "$TS_SRC" "$OUT_DIR/${REGION}.timestamp"

cat > "$OUT_DIR/graphhopper-config.yml" <<CFG
graphhopper:
  datareader.file: /data/${PBF_BASENAME}
  graph.location: /data/graph-cache
  graph.encoded_values: surface,road_class,road_environment,max_speed
  profiles:
    - name: car
      vehicle: car
      weighting: custom
      custom_model_file: /data/gh-mvum.json
      turn_costs: false
  prepare.ch.weightings: []
  prepare.lm.weightings: []
  routing.ch.disabling_allowed: true
  routing.lm.disabling_allowed: true
  import.osm.ignored_highways: footway,cycleway,path,steps
CFG

cat <<MSG
Running GraphHopper prep for region '$REGION'
- PBF: $OUT_DIR/$PBF_BASENAME
- Custom model: $OUT_DIR/gh-mvum.json
- Config: $OUT_DIR/graphhopper-config.yml
- Output dir (host mount): $OUT_DIR
- Image: $GH_IMAGE
MSG

docker run --rm \
  -v "$OUT_DIR":/data \
  "$GH_IMAGE" \
  /bin/bash -lc "cd /data && graphhopper.sh import graphhopper-config.yml"

# Package GHZ (graph-cache + metadata) using Python zip for portability.
PY_BIN="$(command -v python3 || command -v python || true)"
if [[ -z "$PY_BIN" ]]; then
  echo "ERROR: python3/python not found in PATH for packaging GHZ." >&2
  exit 4
fi
OUT_DIR="$OUT_DIR" REGION="$REGION" "$PY_BIN" - <<'PY'
import os, zipfile, sys
out_dir = os.path.abspath(os.getenv('OUT_DIR', '.'))
region = os.getenv('REGION', 'sample')
zip_path = os.path.join(out_dir, f"{region}.ghz")
cache_dir = os.path.join(out_dir, "graph-cache")
if not os.path.isdir(cache_dir):
    sys.exit("graph-cache not found; GraphHopper import likely failed")
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(cache_dir):
        for name in files:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, out_dir)
            zf.write(full, rel)
    for extra in (f"{region}.poly", f"{region}.timestamp", "gh-mvum.json"):
        full = os.path.join(out_dir, extra)
        if os.path.isfile(full):
            zf.write(full, extra)
print(f"Wrote {zip_path}")
PY

echo "GraphHopper GHZ ready in $OUT_DIR/${REGION}.ghz"
