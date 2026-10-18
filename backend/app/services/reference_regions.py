"""CSV-backed reference-region data with authoritative administrative geometry.

The supplied CSV is district-level data.  Geometry is therefore sourced from
the matching Indian ADM2 boundary release rather than approximating an area
from a district name or a point.  A small cache in ``database`` lets the map
continue to load after the first successful retrieval without modifying the
source CSV or any user-owned project record.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from app.services.json_storage import DATA_DIR, atomic_write


ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = ROOT / "sundarbans_mangrove_reference_data.csv"
CACHE_PATH = DATA_DIR / "reference_regions_cache.json"
BOUNDARY_URL = (
    "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/"
    "gbOpen/IND/ADM2/geoBoundaries-IND-ADM2_simplified.geojson"
)
BOUNDARY_ATTRIBUTION = (
    "geoBoundaries gbOpen IND ADM2 (2021), source: Pathways Data Pvt. Ltd. "
    "and lgdirectory.gov.in, ODbL 1.0"
)

# CSV names do not always use the official spelling used by the boundary file.
# This is an explicit, reviewable mapping; unmatched rows are never drawn.
BOUNDARY_NAME_BY_DISTRICT = {
    "purba medinipur": "Purba Medinipur",
    "north 24 parganas": "North Twenty Four Parganas",
    "south 24 parganas": "South Twenty Four Parganas",
}


def _records() -> list[dict[str, str]]:
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def reference_records() -> list[dict[str, str]]:
    """Return CSV rows exactly as supplied, with no synthetic statistics."""
    return _records()


def _cache() -> dict | None:
    try:
        cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return cached if cached.get("type") == "FeatureCollection" else None
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _download_boundary_features() -> list[dict]:
    try:
        with urlopen(BOUNDARY_URL, timeout=20) as response:  # nosec B310: fixed public dataset URL
            payload = json.load(response)
    except (OSError, URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "Reference boundary data is unavailable. Connect to the boundary "
            "source once so the local cache can be created."
        ) from exc
    features = payload.get("features")
    if not isinstance(features, list):
        raise RuntimeError("Reference boundary source returned invalid GeoJSON")
    return features


def reference_feature_collection() -> dict:
    """Match CSV district records to true ADM2 polygon features.

    The response contains only rows that have both valid CSV data and a
    confidently matched boundary.  State totals intentionally remain absent:
    they are aggregate statistics, not a district polygon.
    """
    cached = _cache()
    if cached is not None:
        return cached

    source_features = _download_boundary_features()
    features_by_name = {
        str(feature.get("properties", {}).get("shapeName", "")).casefold(): feature
        for feature in source_features
    }
    output: list[dict] = []
    for row in _records():
        if row.get("source") == "SYNTHETIC_DEMO" or "SYNTHETIC_DEMO" in (row.get("data_status") or ""):
            continue
        district = (row.get("district") or "").strip()
        boundary_name = BOUNDARY_NAME_BY_DISTRICT.get(district.casefold())
        source_feature = features_by_name.get((boundary_name or "").casefold())
        geometry = source_feature.get("geometry") if source_feature else None
        if not geometry or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            continue
        reference_id = f"india-west-bengal-{district.casefold().replace(' ', '-')}"
        output.append(
            {
                "type": "Feature",
                "id": reference_id,
                "geometry": geometry,
                "properties": {
                    "reference_id": reference_id,
                    "country": row.get("country"),
                    "state": row.get("state"),
                    "district": district,
                    "region": row.get("region"),
                    "assessment_year": row.get("assessment_year"),
                    "very_dense_mangrove_km2": row.get("very_dense_mangrove_km2"),
                    "moderately_dense_mangrove_km2": row.get("moderately_dense_mangrove_km2"),
                    "open_mangrove_km2": row.get("open_mangrove_km2"),
                    "total_mangrove_cover_km2": row.get("total_mangrove_cover_km2"),
                    "change_vs_2021_km2": row.get("change_vs_2021_km2"),
                    "tree_count": row.get("tree_count"),
                    "carbon_stock_tonnes": row.get("carbon_stock_tonnes"),
                    "data_status": row.get("data_status"),
                    "boundary_name": boundary_name,
                    "boundary_source": BOUNDARY_ATTRIBUTION,
                },
            }
        )
    collection = {
        "type": "FeatureCollection",
        "features": output,
        "metadata": {
            "boundary_source": BOUNDARY_ATTRIBUTION,
            "boundary_url": BOUNDARY_URL,
            "matched_region_count": len(output),
            "unmatched_csv_rows": [
                row.get("district")
                for row in _records()
                if row.get("source") != "SYNTHETIC_DEMO"
                and "SYNTHETIC_DEMO" not in (row.get("data_status") or "")
                and row.get("district", "").casefold() not in BOUNDARY_NAME_BY_DISTRICT
            ],
        },
    }
    # The cache is derived data only.  It contains no account, project, or
    # audit data, and is atomically written to avoid a partial map payload.
    atomic_write(CACHE_PATH, collection)
    return collection


def reference_properties(reference_id: str) -> dict | None:
    for feature in reference_feature_collection().get("features", []):
        if feature.get("id") == reference_id:
            return feature.get("properties", {})
    return None
