#!/usr/bin/env bash
set -euo pipefail

# Preprocess OSM data for OSRM (extract + partition + customize).
# Requires Docker and pulls osrm/osrm-backend:v5.27.0.

ROOT_DIR=$(cd -- "$(dirname "$0")/.." && pwd)
REGION=${OSRM_REGION:-sample}
PBF_SRC=${OSRM_PBF:-"$ROOT_DIR/data/osm/${REGION}.osm.pbf"}
DATA_ROOT=${OSRM_DATA_ROOT:-"$ROOT_DIR/data/osm"}
PROFILE_SRC=${OSRM_PROFILE:-"$ROOT_DIR/profiles/car.lua"}
OVERRIDE_SRC=${MVUM_SPEED_OVERRIDES:-"$ROOT_DIR/profiles/mvum_speed_overrides.csv"}

OUT_DIR="$DATA_ROOT/$REGION"
mkdir -p "$OUT_DIR"

if [[ ! -f "$PBF_SRC" ]]; then
  echo "PBF not found: $PBF_SRC" >&2
  exit 2
fi
if [[ ! -f "$PROFILE_SRC" ]]; then
  echo "Profile not found: $PROFILE_SRC" >&2
  exit 3
fi

PBF_BASENAME="${REGION}.osm.pbf"
cp -f "$PBF_SRC" "$OUT_DIR/$PBF_BASENAME"
cp -f "$PROFILE_SRC" "$OUT_DIR/car.lua"
if [[ -f "$OVERRIDE_SRC" ]]; then
  cp -f "$OVERRIDE_SRC" "$OUT_DIR/mvum_speed_overrides.csv"
fi

cat <<MSG
Running OSRM prep for region '$REGION'
- PBF: $OUT_DIR/$PBF_BASENAME
- Profile: $OUT_DIR/car.lua
- Output dir: $OUT_DIR
MSG

docker run --rm \
  -v "$OUT_DIR":/data \
  osrm/osrm-backend:v5.27.0 \
  /bin/sh -c "cd /data && osrm-extract -p car.lua $PBF_BASENAME && osrm-partition ${REGION}.osrm && osrm-customize ${REGION}.osrm"

echo "OSRM data ready in $OUT_DIR"
