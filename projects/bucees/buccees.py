#!/usr/bin/env python3
"""
Fetch the Buc-ee's webmap layers as KML and package into a KMZ.
Source webmap: https://www.arcgis.com/apps/mapviewer/index.html?webmap=d76f7166f7cf409895b8b95219ace470
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import List
from zipfile import ZipFile, ZIP_DEFLATED
import html

ITEM_ID = "d76f7166f7cf409895b8b95219ace470"
ARCGIS_WEBMAP_URL = f"https://www.arcgis.com/sharing/rest/content/items/{ITEM_ID}/data"
OUTPUT_DIR = Path("outputs")
KMZ_NAME = OUTPUT_DIR / "bucees.kmz"


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url) as resp:
        return json.load(resp)


def fetch_webmap_json() -> dict:
    return fetch_json(f"{ARCGIS_WEBMAP_URL}?f=json")


def layer_info(webmap: dict) -> List[tuple[str, str, str]]:
    """
    Return list of (title, query_url, layer_url) for each operational layer.
    """
    items = []
    for layer in webmap.get("operationalLayers", []):
        url = layer.get("url")
        title = layer.get("title", "") or Path(url or "").name
        if not url:
            continue
        # Keep only the Buc-ee's layers; skip basemap/other references.
        if "buc" not in title.lower():
            continue
        query_url = f"{url}/query?where=1=1&outFields=*&f=geojson"
        items.append((title, query_url, url))
    return items


def fetch_geojson(url: str) -> dict:
    return fetch_json(url)


def pick_name(props: dict) -> str:
    for key in ("NAME", "Name", "name", "TITLE", "Title", "title", "City"):
        if key in props and str(props[key]).strip():
            return str(props[key]).strip()
    for val in props.values():
        if str(val).strip():
            return str(val).strip()
    return "Feature"


def clean_val(val) -> str:
    if val is None:
        return ""
    s = str(val)
    if s.strip().lower() in {"<null>", "null", "none"}:
        return ""
    return s


def xml_escape(val: str) -> str:
    return (
        val.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def get_icon_from_layer(layer_url: str) -> bytes | None:
    """
    Fetch layer metadata and return PNG bytes from imageData if present.
    """
    meta_url = f"{layer_url}?f=pjson"
    try:
        data = fetch_json(meta_url)
        sym = data.get("drawingInfo", {}).get("renderer", {}).get("symbol", {})
        img_b64 = sym.get("imageData")
        if img_b64:
            import base64

            return base64.b64decode(img_b64)
    except Exception:
        return None
    return None


def build_kml(placemarks: list[dict], icon_href: str | None) -> str:
    def placemark_entry(pm: dict) -> str:
        name = xml_escape(pm["name"])
        lon, lat = pm["lon"], pm["lat"]
        props = pm["props"]

        priority = ["Address", "City", "State", "Zip_Code", "Store_Type", "Store_Features"]
        rows = []
        seen = set()
        for key in priority:
            if key in props:
                rows.append(f"<tr><td><b>{key}</b></td><td>{html.escape(clean_val(props[key]))}</td></tr>")
                seen.add(key)
        for k, v in props.items():
            if k in seen:
                continue
            rows.append(f"<tr><td><b>{k}</b></td><td>{html.escape(clean_val(v))}</td></tr>")
        desc = f"<![CDATA[<table>{''.join(rows)}</table>]]>"

        data_rows = "".join(
            f"<Data name=\"{k}\"><displayName>{k}</displayName><value>{xml_escape(clean_val(v))}</value></Data>"
            for k, v in props.items()
        )
        return f"""
    <Placemark>
      <name>{name}</name>
      <description>{desc}</description>
      {'<styleUrl>#buceesIcon</styleUrl>' if icon_href else ''}
      <ExtendedData>{data_rows}</ExtendedData>
      <Point><coordinates>{lon},{lat},0</coordinates></Point>
    </Placemark>"""

    style_block = ""
    if icon_href:
        style_block = f"""
    <Style id="buceesIcon">
      <IconStyle>
        <scale>1.3</scale>
        <Icon><href>{icon_href}</href></Icon>
      </IconStyle>
      <LabelStyle><scale>1.2</scale></LabelStyle>
    </Style>"""

    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document id="root_doc">
    <name>Buc-ee's</name>
    {style_block}
    <Folder>
      <name>Buc-ee's</name>
      {''.join(placemark_entry(pm) for pm in placemarks)}
    </Folder>
  </Document>
</kml>
"""
    return kml


def make_kmz(master_kml_text: str, icon_bytes: bytes | None) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with ZipFile(KMZ_NAME, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("doc.kml", master_kml_text)
        if icon_bytes:
            zf.writestr("files/bucees.png", icon_bytes)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching webmap JSON...")
    webmap = fetch_webmap_json()
    layers = layer_info(webmap)
    if not layers:
        print("No operational layer URLs found in webmap.", file=sys.stderr)
        return 1

    all_pm = []
    for title, url, layer_url in layers:
        try:
            print(f"Fetching GeoJSON: {url}")
            gj = fetch_geojson(url)
            for feat in gj.get("features", []):
                geom = feat.get("geometry") or {}
                if geom.get("type") != "Point":
                    continue
                coords = geom.get("coordinates") or []
                if len(coords) < 2:
                    continue
                lon, lat = coords[0], coords[1]
                props = feat.get("properties") or {}
                name = pick_name(props)
                all_pm.append({"name": name, "lon": lon, "lat": lat, "props": props})
        except Exception as e:
            print(f"WARNING: failed to fetch/convert {url}: {e}", file=sys.stderr)

    if not all_pm:
        print("No layers converted; aborting.", file=sys.stderr)
        return 1

    icon_bytes = get_icon_from_layer(layers[0][2]) if layers else None
    icon_href = "files/bucees.png" if icon_bytes else None
    master_kml = build_kml(all_pm, icon_href=icon_href)

    make_kmz(master_kml, icon_bytes)
    print(f"Created {KMZ_NAME} with {len(all_pm)} locations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
