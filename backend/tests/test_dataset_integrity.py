import csv
from pathlib import Path
from scripts.generate_synthetic_dataset import (
    CSV_PATH,
    ORIGINAL_RECORDS,
    build_and_write_dataset,
    validate_dataset,
)
from app.services.reference_regions import reference_feature_collection, reference_records


def test_dataset_integrity_and_original_records():
    assert CSV_PATH.exists(), "Dataset CSV file must exist"
    result = validate_dataset(CSV_PATH)
    assert result["status"] == "valid"
    assert result["total_records"] == 1004
    assert result["original_count"] == 4
    assert result["synthetic_count"] == 1000


def test_original_four_records_exact_values():
    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    # The first 4 rows must be the exact original records
    original_rows = rows[:4]
    assert len(original_rows) == 4

    for actual, expected in zip(original_rows, ORIGINAL_RECORDS):
        assert actual["district"] == expected["district"]
        assert actual["country"] == expected["country"]
        assert actual["state"] == expected["state"]
        assert actual["region"] == expected["region"]
        assert actual["assessment_year"] == expected["assessment_year"]
        assert actual["very_dense_mangrove_km2"] == expected["very_dense_mangrove_km2"]
        assert actual["moderately_dense_mangrove_km2"] == expected["moderately_dense_mangrove_km2"]
        assert actual["open_mangrove_km2"] == expected["open_mangrove_km2"]
        assert actual["total_mangrove_cover_km2"] == expected["total_mangrove_cover_km2"]
        assert actual["change_vs_2021_km2"] == expected["change_vs_2021_km2"]
        assert actual["data_status"] == expected["data_status"]
        assert actual.get("source", "") != "SYNTHETIC_DEMO"


def test_synthetic_records_explicitly_marked():
    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    synthetic = rows[4:]
    assert len(synthetic) == 1000

    for r in synthetic:
        assert r["data_status"] == "SYNTHETIC_DEMO"
        assert r["source"] == "SYNTHETIC_DEMO"
        # Validate data types and ranges
        v_dense = float(r["very_dense_mangrove_km2"])
        m_dense = float(r["moderately_dense_mangrove_km2"])
        open_m = float(r["open_mangrove_km2"])
        total = float(r["total_mangrove_cover_km2"])
        assert v_dense >= 0
        assert m_dense >= 0
        assert open_m >= 0
        assert round(v_dense + m_dense + open_m, 2) == total
        assert int(r["tree_count"]) > 0
        assert float(r["carbon_stock_tonnes"]) > 0
        lat = float(r["latitude"])
        lon = float(r["longitude"])
        assert 21.0 <= lat <= 23.0
        assert 87.0 <= lon <= 90.0


def test_dataset_idempotency_and_fixed_seed():
    """Rerunning generator must never duplicate records and must produce identical output."""
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        content_before = f.read()

    # Rerun generator
    build_and_write_dataset(CSV_PATH)

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        content_after = f.read()

    assert content_before == content_after, "Generator is not deterministic or created duplicate records"

    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1004


def test_synthetic_records_cannot_become_reference_boundaries():
    """Synthetic records must never be converted into authoritative reference boundaries."""
    collection = reference_feature_collection()
    features = collection.get("features", [])

    # Features must only correspond to authoritative ADM2 boundaries (3 districts)
    assert len(features) == 3
    district_names = {f["properties"]["district"].casefold() for f in features}
    assert district_names == {"purba medinipur", "north 24 parganas", "south 24 parganas"}

    for f in features:
        props = f["properties"]
        assert props.get("data_status") != "SYNTHETIC_DEMO"
        assert props.get("source") != "SYNTHETIC_DEMO"
        assert "Synthetic" not in props.get("district", "")
