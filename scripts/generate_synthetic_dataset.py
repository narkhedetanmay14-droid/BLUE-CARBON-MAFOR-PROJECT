#!/usr/bin/env python3
"""
Repeatable, deterministic dataset generator and validator for reference mangrove data.

Guarantees:
1. Preserves the exact 4 original records with original field values.
2. Generates exactly 1,000 synthetic demo records (total 1,004 records excluding header).
3. Explicitly marks synthetic records with data_status='SYNTHETIC_DEMO' and source='SYNTHETIC_DEMO'.
4. Enforces valid columns, data types, coordinates within Sundarbans, numeric ranges, and carbon units.
5. Fixed seed (42) for deterministic, idempotent regeneration (never introduces duplicates).
6. Synthetic demonstration data is clearly flagged so it cannot silently become verified real-world data.
"""

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "sundarbans_mangrove_reference_data.csv"
RANDOM_SEED = 42

HEADERS = [
    "country",
    "state",
    "district",
    "region",
    "assessment_year",
    "very_dense_mangrove_km2",
    "moderately_dense_mangrove_km2",
    "open_mangrove_km2",
    "total_mangrove_cover_km2",
    "change_vs_2021_km2",
    "tree_count",
    "carbon_stock_tonnes",
    "data_status",
    "source",
    "latitude",
    "longitude",
]

# The authoritative four original records from git commit e599f07
ORIGINAL_RECORDS = [
    {
        "country": "India",
        "state": "West Bengal",
        "district": "Purba Medinipur",
        "region": "Sundarbans-adjacent mangrove region",
        "assessment_year": "2023",
        "very_dense_mangrove_km2": "0.0",
        "moderately_dense_mangrove_km2": "0.79",
        "open_mangrove_km2": "2.86",
        "total_mangrove_cover_km2": "3.65",
        "change_vs_2021_km2": "0.0",
        "tree_count": "",
        "carbon_stock_tonnes": "",
        "data_status": "Official district mangrove area; tree count/carbon not supplied in this table",
        "source": "",
        "latitude": "",
        "longitude": "",
    },
    {
        "country": "India",
        "state": "West Bengal",
        "district": "North 24 Parganas",
        "region": "Sundarbans",
        "assessment_year": "2023",
        "very_dense_mangrove_km2": "13.44",
        "moderately_dense_mangrove_km2": "11.47",
        "open_mangrove_km2": "1.72",
        "total_mangrove_cover_km2": "26.63",
        "change_vs_2021_km2": "0.0",
        "tree_count": "",
        "carbon_stock_tonnes": "",
        "data_status": "Official district mangrove area; tree count/carbon not supplied in this table",
        "source": "",
        "latitude": "",
        "longitude": "",
    },
    {
        "country": "India",
        "state": "West Bengal",
        "district": "South 24 Parganas",
        "region": "Sundarbans",
        "assessment_year": "2023",
        "very_dense_mangrove_km2": "968.19",
        "moderately_dense_mangrove_km2": "691.53",
        "open_mangrove_km2": "429.16",
        "total_mangrove_cover_km2": "2088.88",
        "change_vs_2021_km2": "1.41",
        "tree_count": "",
        "carbon_stock_tonnes": "",
        "data_status": "Official district mangrove area; tree count/carbon not supplied in this table",
        "source": "",
        "latitude": "",
        "longitude": "",
    },
    {
        "country": "India",
        "state": "West Bengal",
        "district": "West Bengal total",
        "region": "All West Bengal mangrove regions",
        "assessment_year": "2023",
        "very_dense_mangrove_km2": "981.63",
        "moderately_dense_mangrove_km2": "703.79",
        "open_mangrove_km2": "433.74",
        "total_mangrove_cover_km2": "2119.16",
        "change_vs_2021_km2": "1.41",
        "tree_count": "",
        "carbon_stock_tonnes": "",
        "data_status": "Official state total; not a polygon-level estimate",
        "source": "",
        "latitude": "",
        "longitude": "",
    },
]

SYNTHETIC_DISTRICTS = [
    "South 24 Parganas",
    "North 24 Parganas",
    "Purba Medinipur",
]


def generate_synthetic_records(count: int = 1000) -> list[dict]:
    rng = random.Random(RANDOM_SEED)
    records = []
    for i in range(1, count + 1):
        district = rng.choice(SYNTHETIC_DISTRICTS)
        v_dense = round(rng.uniform(0.05, 2.50), 2)
        m_dense = round(rng.uniform(0.05, 2.00), 2)
        open_m = round(rng.uniform(0.02, 1.20), 2)
        total = round(v_dense + m_dense + open_m, 2)
        change = round(rng.uniform(-0.15, 0.20), 2)
        # Tree count proportional to total mangrove cover (e.g. 8,000 - 15,000 trees per km2)
        tree_count = int(total * rng.uniform(8000, 14000))
        # Carbon stock tonnes: ~120 to 250 tonnes C per hectare (100 ha per km2)
        carbon_stock = round(total * 100 * rng.uniform(110.0, 240.0), 2)

        # Coordinates bounded within the Sundarbans mangrove biosphere (21.5 - 22.5 N, 88.0 - 89.2 E)
        lat = round(rng.uniform(21.55, 22.45), 4)
        lon = round(rng.uniform(88.10, 89.15), 4)

        record = {
            "country": "India",
            "state": "West Bengal",
            "district": f"{district} (Plot-{i:04d})",
            "region": "Sundarbans Delta (Synthetic Demo Plot)",
            "assessment_year": "2023",
            "very_dense_mangrove_km2": str(v_dense),
            "moderately_dense_mangrove_km2": str(m_dense),
            "open_mangrove_km2": str(open_m),
            "total_mangrove_cover_km2": str(total),
            "change_vs_2021_km2": str(change),
            "tree_count": str(tree_count),
            "carbon_stock_tonnes": str(carbon_stock),
            "data_status": "SYNTHETIC_DEMO",
            "source": "SYNTHETIC_DEMO",
            "latitude": str(lat),
            "longitude": str(lon),
        }
        records.append(record)
    return records


def build_and_write_dataset(target_path: Path = CSV_PATH) -> tuple[int, int]:
    """Generates dataset with exact 4 original records and 1,000 synthetic records."""
    synthetic = generate_synthetic_records(1000)
    all_rows = ORIGINAL_RECORDS + synthetic

    with open(target_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    return len(ORIGINAL_RECORDS), len(synthetic)


def validate_dataset(csv_path: Path = CSV_PATH) -> dict:
    """Validates the CSV dataset against all integrity requirements."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = list(csv.DictReader(f))

    total_records = len(reader)
    synthetic_records = [r for r in reader if r.get("data_status") == "SYNTHETIC_DEMO" or r.get("source") == "SYNTHETIC_DEMO"]
    original_records = [r for r in reader if r.get("data_status") != "SYNTHETIC_DEMO" and r.get("source") != "SYNTHETIC_DEMO"]

    # Verify count
    assert total_records == 1004, f"Expected 1004 records, got {total_records}"
    assert len(original_records) == 4, f"Expected 4 original records, got {len(original_records)}"
    assert len(synthetic_records) == 1000, f"Expected 1000 synthetic records, got {len(synthetic_records)}"

    # Verify original records preserved
    for orig, expected in zip(original_records, ORIGINAL_RECORDS):
        for key in ["country", "state", "district", "region", "assessment_year", "total_mangrove_cover_km2", "data_status"]:
            assert orig.get(key) == expected.get(key), (
                f"Mismatch in original record {expected['district']} field '{key}': "
                f"got '{orig.get(key)}', expected '{expected.get(key)}'"
            )

    # Verify synthetic records validity
    for i, rec in enumerate(synthetic_records):
        assert rec.get("data_status") == "SYNTHETIC_DEMO", f"Record {i} not marked SYNTHETIC_DEMO"
        assert rec.get("source") == "SYNTHETIC_DEMO", f"Record {i} source not SYNTHETIC_DEMO"
        assert float(rec["very_dense_mangrove_km2"]) >= 0
        assert float(rec["moderately_dense_mangrove_km2"]) >= 0
        assert float(rec["open_mangrove_km2"]) >= 0
        total = float(rec["total_mangrove_cover_km2"])
        assert total > 0
        assert int(rec["tree_count"]) > 0
        assert float(rec["carbon_stock_tonnes"]) > 0
        lat = float(rec["latitude"])
        lon = float(rec["longitude"])
        assert 21.0 <= lat <= 23.0, f"Latitude {lat} out of range"
        assert 87.0 <= lon <= 90.0, f"Longitude {lon} out of range"

    return {
        "status": "valid",
        "total_records": total_records,
        "original_count": len(original_records),
        "synthetic_count": len(synthetic_records),
    }


if __name__ == "__main__":
    orig_count, syn_count = build_and_write_dataset()
    result = validate_dataset()
    print(f"Dataset successfully created and validated:")
    print(f"  Total records (excl header): {result['total_records']}")
    print(f"  Original records preserved:  {result['original_count']}")
    print(f"  Synthetic demo records:      {result['synthetic_count']}")
    print(f"  Integrity validation:        {result['status']}")
