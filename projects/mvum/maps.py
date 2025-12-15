#!/usr/bin/env python3

from pathlib import Path
import sys

from functions import (
    add_point_label_folder_from_lines,
    apply_atak_style_and_region,
    colorize_lines_by_access,
    combine_kml_layers,
    duplicate_simpledata_to_data,
    embed_label_points_in_multigeometry,
    ensure_placemark_names,
    get_layer_name,
    harmonize_document_names,
    inject_description_table,
    inject_labelstyle,
    make_kmz,
    make_zip_archive,
    run_export_with_gdal,
)

# ---------------------------
# CONFIG
# ---------------------------
SHAPEFILES_DIR = Path("shapefiles")
OUTPUT_DIR = Path("outputs")

INPUT_SHP_TRAILS = SHAPEFILES_DIR / "MVUM_Symbology_-_Motor_Vehicle_Use_Map_Trails.shp"
INPUT_SHP_ROADS = SHAPEFILES_DIR / "MVUM_Symbology_-_Motor_Vehicle_Use_Map_Roads.shp"
OUTPUT_KML = OUTPUT_DIR / INPUT_SHP_TRAILS.with_suffix(".kml").name
OUTPUT_KMZ = OUTPUT_DIR / INPUT_SHP_TRAILS.with_suffix(".kmz").name
# Force stable KML layer/schema names to match legacy exports.
LAYER_EXPORT_NAME_TRAILS = "mvum_symbology__motor_vehicle_use_map_trails"
LAYER_EXPORT_NAME_ROADS = "mvum_symbology__motor_vehicle_use_map_roads"
# Optional spatial filter (minx, miny, maxx, maxy). Set to None for all data.
SPATIAL_FILTER: tuple[float, float, float, float] | None = None

# Generate per-state KMLs using coarse bounding boxes; all are packaged into the KMZ.
# Set RUN_ALL_STATES=True to use the full STATE_BBOXES list instead of the
# default subset (CO).
RUN_ALL_STATES = False
GENERATE_STATE_KMLS = True
STATE_ARCHIVE_ZIP = OUTPUT_DIR / "MVUM_states.zip"
STATE_BBOXES: dict[str, tuple[float, float, float, float]] = {
    "CO": (-109.060253, 36.992426, -102.041524, 41.003444),
}
STATE_BBOXES_ALL: dict[str, tuple[float, float, float, float]] = STATE_BBOXES.copy()

# Fields to try (in order) for ATAK labels; first non-empty wins.
# LONGNAME is populated from the shapefile's NAME field so we retain
# the original NAME attribute in ExtendedData instead of losing it to <name>.
LABEL_FIELDS: list[str] = ["ID", "LONGNAME"]
LABEL_POINT_FOLDER_NAME = "Trail Labels (points)"
# If True, add a Point into each Placemark's geometry (as MultiGeometry) so
# ATAK can render labels anchored to the point while retaining the line.
EMBED_LABEL_POINTS = True
ACCESS_FIELDS_TRAILS = [
    "PASSENGERV",
    "HIGHCLEARA",
    "ATV",
    "TRUCK",
    "MOTORCYCLE",
    # Include tracked/snowmobile style access flags if present.
    "SNOWMOBILE",
    "TRACKED_OH",
    "TRACKED__2",
]
ACCESS_COLOR_ALLOWED = "ff00ff00"  # green (AA BB GG RR)
ACCESS_COLOR_DENIED = "ff0000ff"   # red

# Roads-specific styling
ACCESS_FIELDS_ROADS = ACCESS_FIELDS_TRAILS
ROADS_COLOR_ALLOWED = "ff00a5ff"  # orange (AABBGGRR)
ROADS_COLOR_DENIED = "ff0000ff"   # red

# LineStyle (KML AABBGGRR)
LINE_COLOR = "ff0000ff"   # red (base; overridden inline per feature)
LINE_WIDTH = "2"          # px

# LabelStyle (KML AABBGGRR)
LABEL_COLOR = "ff00ffff"  # yellow
LABEL_SCALE = "1.5"

# ATAK map-specific customizations. Adjust these values to change how the
# generated KML/KMZ looks when loaded in ATAK.
ENABLE_ATAK_STYLE = True
ATAK_STYLE_ID_TRAILS = "AtakStyleTrails"
ATAK_STYLE_ID_ROADS = "AtakStyleRoads"
# Set to a filename or URL if you want an icon; None means omit IconStyle.
ATAK_ICON_HREF: str | None = None
ATAK_ICON_SCALE = "2.0"
ATAK_POLY_COLOR = "ff000000"
ATAK_POLY_OUTLINE = "0"
ATAK_REGION = None


def main() -> int:
    trails_shp = Path(INPUT_SHP_TRAILS)
    roads_shp = Path(INPUT_SHP_ROADS)
    if not trails_shp.exists():
        print(f"ERROR: Trails shapefile not found: {trails_shp}", file=sys.stderr)
        return 2
    if not roads_shp.exists():
        print(f"ERROR: Roads shapefile not found: {roads_shp}", file=sys.stderr)
        return 2

    trail_layer_name = get_layer_name(str(trails_shp))
    road_layer_name = get_layer_name(str(roads_shp))

    extras = []
    if ENABLE_ATAK_STYLE and ATAK_ICON_HREF:
        icon_path = Path(ATAK_ICON_HREF)
        if icon_path.exists():
            extras.append(ATAK_ICON_HREF)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SHAPEFILES_DIR.mkdir(parents=True, exist_ok=True)

    state_bboxes = STATE_BBOXES_ALL if RUN_ALL_STATES else STATE_BBOXES

    if GENERATE_STATE_KMLS:
        print("Generating per-state KMLs/KMZs (roads + trails)...")
        produced_kmzs: list[str] = []
        for state, bbox in state_bboxes.items():
            # Trails
            out_trails = OUTPUT_DIR / f"MVUM_{state}_trails.kml"
            run_export_with_gdal(
                str(trails_shp),
                str(out_trails),
                trail_layer_name,
                bbox,
                LAYER_EXPORT_NAME_TRAILS,
                LINE_COLOR,
                LINE_WIDTH,
            )
            n_trail_names = ensure_placemark_names(out_trails, LABEL_FIELDS, overwrite=True)
            inject_labelstyle(out_trails, LABEL_COLOR, LABEL_SCALE)
            harmonize_document_names(out_trails, LAYER_EXPORT_NAME_TRAILS)
            if ENABLE_ATAK_STYLE:
                apply_atak_style_and_region(
                    out_trails,
                    style_id=ATAK_STYLE_ID_TRAILS,
                    icon_href=ATAK_ICON_HREF,
                    icon_scale=ATAK_ICON_SCALE,
                    poly_color=ATAK_POLY_COLOR,
                    poly_outline=ATAK_POLY_OUTLINE,
                    label_color=LABEL_COLOR,
                    label_scale=LABEL_SCALE,
                    line_color=LINE_COLOR,
                    line_width=LINE_WIDTH,
                    region=None,
                )
            if EMBED_LABEL_POINTS:
                embed_label_points_in_multigeometry(str(trails_shp), out_trails, label_fields=LABEL_FIELDS)
            else:
                add_point_label_folder_from_lines(
                    str(trails_shp),
                    out_trails,
                    folder_name=LABEL_POINT_FOLDER_NAME,
                    style_id=ATAK_STYLE_ID_TRAILS if ENABLE_ATAK_STYLE else "",
                    label_fields=LABEL_FIELDS,
                    schema_id=LAYER_EXPORT_NAME_TRAILS,
                )
            duplicate_simpledata_to_data(out_trails)
            inject_description_table(out_trails)
            colorize_lines_by_access(
                out_trails,
                allow_fields=ACCESS_FIELDS_TRAILS,
                color_allowed=ACCESS_COLOR_ALLOWED,
                color_denied=ACCESS_COLOR_DENIED,
                width=LINE_WIDTH,
            )

            # Roads
            out_roads = OUTPUT_DIR / f"MVUM_{state}_roads.kml"
            run_export_with_gdal(
                str(roads_shp),
                str(out_roads),
                road_layer_name,
                bbox,
                LAYER_EXPORT_NAME_ROADS,
                LINE_COLOR,
                LINE_WIDTH,
            )
            n_road_names = ensure_placemark_names(out_roads, LABEL_FIELDS, overwrite=True)
            inject_labelstyle(out_roads, LABEL_COLOR, LABEL_SCALE)
            harmonize_document_names(out_roads, LAYER_EXPORT_NAME_ROADS)
            if ENABLE_ATAK_STYLE:
                apply_atak_style_and_region(
                    out_roads,
                    style_id=ATAK_STYLE_ID_ROADS,
                    icon_href=ATAK_ICON_HREF,
                    icon_scale=ATAK_ICON_SCALE,
                    poly_color=ATAK_POLY_COLOR,
                    poly_outline=ATAK_POLY_OUTLINE,
                    label_color=LABEL_COLOR,
                    label_scale=LABEL_SCALE,
                    line_color=LINE_COLOR,
                    line_width=LINE_WIDTH,
                    region=None,
                )
            if EMBED_LABEL_POINTS:
                embed_label_points_in_multigeometry(str(roads_shp), out_roads, label_fields=LABEL_FIELDS)
            else:
                add_point_label_folder_from_lines(
                    str(roads_shp),
                    out_roads,
                    folder_name=LABEL_POINT_FOLDER_NAME,
                    style_id=ATAK_STYLE_ID_ROADS if ENABLE_ATAK_STYLE else "",
                    label_fields=LABEL_FIELDS,
                    schema_id=LAYER_EXPORT_NAME_ROADS,
                )
            duplicate_simpledata_to_data(out_roads)
            inject_description_table(out_roads)
            colorize_lines_by_access(
                out_roads,
                allow_fields=ACCESS_FIELDS_ROADS,
                color_allowed=ROADS_COLOR_ALLOWED,
                color_denied=ROADS_COLOR_DENIED,
                width=LINE_WIDTH,
            )

            combined = OUTPUT_DIR / f"MVUM_{state}.kml"
            combine_kml_layers(out_trails, out_roads, combined, doc_name="MVUM Roads and Trails")

            # Per-state KMZ for ATAK import (combined)
            state_kmz = OUTPUT_DIR / f"MVUM_{state}.kmz"
            make_kmz(combined, state_kmz, extra_files=extras)
            produced_kmzs.append(state_kmz)
            print(f"State {state}: trails named {n_trail_names}, roads named {n_road_names}, files {combined}, {state_kmz}")

        make_zip_archive(produced_kmzs, STATE_ARCHIVE_ZIP)
        zip_size_mb = Path(STATE_ARCHIVE_ZIP).stat().st_size / (1024 * 1024)
        print(f"Created archive: {STATE_ARCHIVE_ZIP} ({zip_size_mb:.1f} MB) containing {len(produced_kmzs)} state KMZs.")
    else:
        # Whole-dataset (non-state) paths
        trails_out = OUTPUT_KML
        run_export_with_gdal(
            str(trails_shp),
            str(trails_out),
            trail_layer_name,
            SPATIAL_FILTER,
            LAYER_EXPORT_NAME_TRAILS,
            LINE_COLOR,
            LINE_WIDTH,
        )
        n_trail_names = ensure_placemark_names(trails_out, LABEL_FIELDS, overwrite=True)
        inject_labelstyle(trails_out, LABEL_COLOR, LABEL_SCALE)
        harmonize_document_names(trails_out, LAYER_EXPORT_NAME_TRAILS)
        if ENABLE_ATAK_STYLE:
            apply_atak_style_and_region(
                trails_out,
                style_id=ATAK_STYLE_ID_TRAILS,
                icon_href=ATAK_ICON_HREF,
                icon_scale=ATAK_ICON_SCALE,
                poly_color=ATAK_POLY_COLOR,
                poly_outline=ATAK_POLY_OUTLINE,
                label_color=LABEL_COLOR,
                label_scale=LABEL_SCALE,
                line_color=LINE_COLOR,
                line_width=LINE_WIDTH,
                region=ATAK_REGION,
            )
        if EMBED_LABEL_POINTS:
            embed_label_points_in_multigeometry(str(trails_shp), trails_out, label_fields=LABEL_FIELDS)
        else:
            add_point_label_folder_from_lines(
                str(trails_shp),
                trails_out,
                folder_name=LABEL_POINT_FOLDER_NAME,
                style_id=ATAK_STYLE_ID_TRAILS if ENABLE_ATAK_STYLE else "",
                label_fields=LABEL_FIELDS,
                schema_id=LAYER_EXPORT_NAME_TRAILS,
            )
        duplicate_simpledata_to_data(trails_out)
        inject_description_table(trails_out)
        colorize_lines_by_access(
            trails_out,
            allow_fields=ACCESS_FIELDS_TRAILS,
            color_allowed=ACCESS_COLOR_ALLOWED,
            color_denied=ACCESS_COLOR_DENIED,
            width=LINE_WIDTH,
        )

        roads_out = OUTPUT_DIR / Path(INPUT_SHP_ROADS).with_suffix(".kml").name
        run_export_with_gdal(
            str(roads_shp),
            str(roads_out),
            road_layer_name,
            SPATIAL_FILTER,
            LAYER_EXPORT_NAME_ROADS,
            LINE_COLOR,
            LINE_WIDTH,
        )
        n_road_names = ensure_placemark_names(roads_out, LABEL_FIELDS, overwrite=True)
        inject_labelstyle(roads_out, LABEL_COLOR, LABEL_SCALE)
        harmonize_document_names(roads_out, LAYER_EXPORT_NAME_ROADS)
        if ENABLE_ATAK_STYLE:
            apply_atak_style_and_region(
                roads_out,
                style_id=ATAK_STYLE_ID_ROADS,
                icon_href=ATAK_ICON_HREF,
                icon_scale=ATAK_ICON_SCALE,
                poly_color=ATAK_POLY_COLOR,
                poly_outline=ATAK_POLY_OUTLINE,
                label_color=LABEL_COLOR,
                label_scale=LABEL_SCALE,
                line_color=LINE_COLOR,
                line_width=LINE_WIDTH,
                region=ATAK_REGION,
            )
        if EMBED_LABEL_POINTS:
            embed_label_points_in_multigeometry(str(roads_shp), roads_out, label_fields=LABEL_FIELDS)
        else:
            add_point_label_folder_from_lines(
                str(roads_shp),
                roads_out,
                folder_name=LABEL_POINT_FOLDER_NAME,
                style_id=ATAK_STYLE_ID_ROADS if ENABLE_ATAK_STYLE else "",
                label_fields=LABEL_FIELDS,
                schema_id=LAYER_EXPORT_NAME_ROADS,
            )
        duplicate_simpledata_to_data(roads_out)
        inject_description_table(roads_out)
        colorize_lines_by_access(
            roads_out,
            allow_fields=ACCESS_FIELDS_ROADS,
            color_allowed=ROADS_COLOR_ALLOWED,
            color_denied=ROADS_COLOR_DENIED,
            width=LINE_WIDTH,
        )

        combined = OUTPUT_DIR / "MVUM_roads_trails.kml"
        combine_kml_layers(trails_out, roads_out, combined, doc_name="MVUM Roads and Trails")
        make_kmz(combined, OUTPUT_KMZ, extra_files=extras)
        kmz_size_mb = OUTPUT_KMZ.stat().st_size / (1024 * 1024)
        print(f"Created KMZ: {OUTPUT_KMZ} ({kmz_size_mb:.1f} MB)")

        print(f"Done: {combined}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

