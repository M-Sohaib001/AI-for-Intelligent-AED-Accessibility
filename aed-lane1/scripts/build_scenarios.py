"""
PERSON B — 30-SCENARIO DRAFT GENERATOR
Lane 1: Discovery & Routing

Purpose:
Generate exactly 30 geographically grounded, temporally grounded draft
scenarios from the frozen AED dataset and frozen Woodlands study boundary.

*IMPORTANT*
These are DRAFT scenarios only.

This script:
    - does NOT determine final feasibility
    - does NOT assign true_feasible_aed_ids
    - does NOT label scenarios as feasible/infeasible
    - does NOT modify the frozen AED dataset
    - does NOT modify the frozen study boundary

Person C independently labels the scenarios later.
Person A performs graph sanity checks.
The team then adjudicates disagreements before ground_truth.json is frozen.

Special handling:
The roadmap originally requested >=2 scenarios for every stratum.

The frozen Woodlands data contains:
    - 523 AEDs inside the final boundary
    - 0 AEDs inside Woodlands with blank OPERATING_HOURS

Therefore "unknown_hours" cannot honestly receive 2 scenarios.

Rather than inventing records, this script:
    - creates 0 unknown_hours scenarios
    - records the unavailable stratum explicitly
    - redistributes those two scenarios across valid strata
    - still produces exactly 30 total scenarios
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


AED_DATASET = Path("data/scdf_aed_frozen.geojson")
BOUNDARY_PATH = Path("data/district_boundary.geojson")
OUTPUT_PATH = Path("data/scenarios_draft.json")

RANDOM_SEED = 42
TARGET_SCENARIO_COUNT = 30

# SCENARIO STRATA
STRATA = [
    "normal_daytime",
    "after_hours",
    "boundary_time",
    "closed_aed",
    "unknown_hours",
    "relational_location",
    "missing_floor",
    "multiple_candidate_aeds",
    "no_feasible_aed",
    "outside_district",
    "baseline_system_disagreement",
]

# Because unknown_hours does not exist inside the frozen study area, the
# target allocation below deliberately assigns zero to that stratum.

# The total is exactly 30.
TARGET_COUNTS = {
    "normal_daytime": 4,
    "after_hours": 3,
    "boundary_time": 3,
    "closed_aed": 3,
    "unknown_hours": 0,
    "relational_location": 3,
    "missing_floor": 2,
    "multiple_candidate_aeds": 3,
    "no_feasible_aed": 3,
    "outside_district": 3,
    "baseline_system_disagreement": 3,
}

# DATE/TIME TEMPLATES
NORMAL_TIMES = [
    "2026-08-15T10:30:00",
    "2026-08-15T14:30:00",
    "2026-08-16T11:00:00",
    "2026-08-16T15:30:00",
]

AFTER_HOURS_TIMES = [
    "2026-08-15T23:00:00",
    "2026-08-16T22:30:00",
    "2026-08-17T23:30:00",
]

BOUNDARY_TIMES = [
    "2026-08-15T07:00:00",
    "2026-08-15T17:00:00",
    "2026-08-16T23:59:00",
]

# Times deliberately chosen when common Woodlands AED schedules are likely
# to produce interesting distinctions. They are NOT feasibility labels.
CLOSED_TIMES = [
    "2026-08-15T03:00:00",
    "2026-08-16T04:30:00",
    "2026-08-17T02:00:00",
]

RELATIONAL_TIMES = [
    "2026-08-15T13:00:00",
    "2026-08-16T15:00:00",
    "2026-08-17T18:00:00",
]

MISSING_FLOOR_TIMES = [
    "2026-08-15T14:00:00",
    "2026-08-16T16:00:00",
]

MULTIPLE_CANDIDATE_TIMES = [
    "2026-08-15T12:00:00",
    "2026-08-15T18:00:00",
    "2026-08-16T14:00:00",
]

NO_FEASIBLE_TIMES = [
    "2026-08-15T03:30:00",
    "2026-08-16T04:00:00",
    "2026-08-17T02:30:00",
]

BASELINE_DISAGREEMENT_TIMES = [
    "2026-08-15T09:00:00",
    "2026-08-16T13:30:00",
    "2026-08-17T19:00:00",
]

OUTSIDE_DISTRICT_TIMES = [
    "2026-08-15T14:30:00",
    "2026-08-16T22:00:00",
    "2026-08-17T10:00:00",
]

# DATA LOADING
def load_frozen_aed_dataset(path: Path) -> pd.DataFrame:
    """Load the frozen AED GeoJSON into a DataFrame."""

    if not path.exists():
        raise FileNotFoundError(
            f"Frozen AED dataset not found: {path}"
        )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})

        coordinates = geometry.get("coordinates")

        if not coordinates or len(coordinates) < 2:
            continue

        lon, lat = coordinates[:2]

        rows.append(
            {
                **properties,
                "lon": float(lon),
                "lat": float(lat),
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        raise RuntimeError("Frozen AED dataset contains no usable records.")

    return df


def load_frozen_boundary(path: Path) -> gpd.GeoDataFrame:
    """Load the frozen official Woodlands boundary."""

    if not path.exists():
        raise FileNotFoundError(
            f"Frozen study boundary not found: {path}"
        )

    boundary = gpd.read_file(path)

    if boundary.empty:
        raise RuntimeError("Frozen study boundary contains no geometry.")

    if boundary.crs is None:
        raise RuntimeError(
            "Frozen study boundary has no CRS."
        )

    return boundary


def restrict_to_study_area(
    df: pd.DataFrame,
    boundary: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """
    Keep AEDs covered by the frozen official boundary.

    'covered_by' is used so AEDs exactly on the boundary are retained.
    """

    aed_gdf = gpd.GeoDataFrame(
        df.copy(),
        geometry=gpd.points_from_xy(
            df["lon"],
            df["lat"],
        ),
        crs="EPSG:4326",
    )

    boundary = boundary.to_crs(aed_gdf.crs)

    study_area = gpd.sjoin(
        aed_gdf,
        boundary[["geometry"]],
        how="inner",
        predicate="covered_by",
    )

    study_area = study_area.drop(
        columns=["geometry", "index_right"],
        errors="ignore",
    )

    return pd.DataFrame(study_area).reset_index(drop=True)

# BASIC FIELD HELPERS
def clean_text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, float) and math.isnan(value):
        return ""

    return str(value).strip()


def operating_hours(row) -> str:
    return clean_text(row.get("OPERATING_HOURS"))


def location_description(row) -> str:
    return clean_text(row.get("AED_LOCATION_DESCRIPTION"))


def floor_level(row) -> str:
    return clean_text(row.get("AED_LOCATION_FLOOR_LEVEL"))


def building_name(row) -> str:
    return clean_text(row.get("BUILDING_NAME"))


def has_relational_language(row) -> bool:
    text = location_description(row).lower()

    terms = [
        "near",
        "beside",
        "opposite",
        "behind",
        "next to",
        "across from",
    ]

    return any(term in text for term in terms)


def has_missing_floor(row) -> bool:
    return not floor_level(row)


def is_blank_hours(row) -> bool:
    return not operating_hours(row)


def is_closed_schedule(row) -> bool:
    """
    Identify records whose recorded schedule is explicitly closed.

    This is only used to select a candidate AED for a scenario.
    It does NOT mean the final scenario is labeled infeasible.
    """

    text = operating_hours(row).lower()

    if not text:
        return False

    return "closed" in text


def has_multiple_segments(row) -> bool:
    """
    Multiple recorded schedule segments separated by semicolons.

    This is a registry/text property, not a feasibility judgment.
    """

    text = operating_hours(row)

    return text.count(";") > 1

# RECORD SELECTION
def shuffled_indices(
    df: pd.DataFrame,
    seed: int = RANDOM_SEED,
) -> list[int]:
    rng = random.Random(seed)
    indices = list(df.index)
    rng.shuffle(indices)
    return indices


def select_records(
    df: pd.DataFrame,
    predicate,
    count: int,
    seed_offset: int = 0,
) -> list[pd.Series]:
    """
    Select distinct records satisfying predicate.

    Records are selected deterministically with a fixed random seed.
    """

    candidates = [
        idx
        for idx in shuffled_indices(
            df,
            RANDOM_SEED + seed_offset,
        )
        if predicate(df.loc[idx])
    ]

    if len(candidates) < count:
        raise RuntimeError(
            f"Cannot generate {count} scenarios from the requested "
            f"stratum. Matching records available: {len(candidates)}"
        )

    return [df.loc[idx] for idx in candidates[:count]]


def select_distinct_records(
    df: pd.DataFrame,
    predicate,
    count: int,
    used_ids: set[str],
    seed_offset: int,
) -> list[pd.Series]:
    """
    Select records satisfying predicate while avoiding previously selected
    AED IDs where possible.
    """

    candidates = []

    for idx in shuffled_indices(
        df,
        RANDOM_SEED + seed_offset,
    ):
        row = df.loc[idx]
        aed_id = clean_text(row.get("AED_ID"))

        if aed_id in used_ids:
            continue

        if predicate(row):
            candidates.append(row)

        if len(candidates) >= count:
            break

    if len(candidates) < count:
        # Fall back to unused-coordinate records if the AED ID field is
        # missing or repeated.
        candidates = []

        for idx in shuffled_indices(
            df,
            RANDOM_SEED + seed_offset + 1000,
        ):
            row = df.loc[idx]

            if predicate(row):
                candidates.append(row)

            if len(candidates) >= count:
                break

    if len(candidates) < count:
        raise RuntimeError(
            f"Cannot generate {count} distinct records for this stratum. "
            f"Matching records available: {len(candidates)}"
        )

    return candidates[:count]

# SCENARIO CONSTRUCTION
def make_inside_scenario(
    scenario_id: str,
    category: str,
    row: pd.Series,
    dt: str,
    selection_basis: str,
) -> dict:
    """
    Construct an unlabeled draft scenario.

    No feasibility information is included.
    """

    return {
        "scenario_id": scenario_id,
        "category": category,
        "start_lat": round(float(row["lat"]), 7),
        "start_lon": round(float(row["lon"]), 7),
        "datetime": dt,
        "selection_basis": selection_basis,
    }


def make_outside_scenario(
    scenario_id: str,
    category: str,
    point: Point,
    dt: str,
    selection_basis: str,
) -> dict:
    """Construct an outside-boundary draft scenario."""

    return {
        "scenario_id": scenario_id,
        "category": category,
        "start_lat": round(float(point.y), 7),
        "start_lon": round(float(point.x), 7),
        "datetime": dt,
        "selection_basis": selection_basis,
    }

# OUTSIDE-BOUNDARY POINTS
def make_outside_points(
    boundary: gpd.GeoDataFrame,
    count: int,
) -> list[Point]:
    """
    Generate deterministic points just outside the frozen boundary.

    These are not AED records.

    The points are derived from the boundary's bounding box and tested to
    ensure they are actually outside the frozen polygon.
    """

    boundary_wgs84 = boundary.to_crs("EPSG:4326")

    union = boundary_wgs84.geometry.union_all()

    minx, miny, maxx, maxy = union.bounds

    # Small geographic offsets. The values are deliberately modest so the
    # points remain near the study boundary.
    candidate_points = [
        Point(minx - 0.0020, (miny + maxy) / 2),
        Point(maxx + 0.0020, (miny + maxy) / 2),
        Point((minx + maxx) / 2, miny - 0.0020),
        Point((minx + maxx) / 2, maxy + 0.0020),
        Point(minx - 0.0010, miny - 0.0010),
        Point(maxx + 0.0010, maxy + 0.0010),
    ]

    outside = [
        p
        for p in candidate_points
        if not union.covers(p)
    ]

    if len(outside) < count:
        raise RuntimeError(
            f"Could only construct {len(outside)} outside-boundary "
            f"points; required {count}."
        )

    return outside[:count]

# VALIDATION
def validate_scenarios(
    scenarios: list[dict],
    boundary: gpd.GeoDataFrame,
) -> None:
    """Validate structural and geographic properties of the draft."""

    if len(scenarios) != TARGET_SCENARIO_COUNT:
        raise RuntimeError(
            f"Expected {TARGET_SCENARIO_COUNT} scenarios, "
            f"generated {len(scenarios)}."
        )

    ids = [s["scenario_id"] for s in scenarios]

    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate scenario IDs detected.")

    for scenario in scenarios:
        required = {
            "scenario_id",
            "category",
            "start_lat",
            "start_lon",
            "datetime",
        }

        missing = required - set(scenario)

        if missing:
            raise RuntimeError(
                f"{scenario['scenario_id']} is missing fields: {missing}"
            )

        if "true_feasible_aed_ids" in scenario:
            raise RuntimeError(
                "Draft scenarios must NOT contain true_feasible_aed_ids."
            )

        point = Point(
            float(scenario["start_lon"]),
            float(scenario["start_lat"]),
        )

        boundary_wgs84 = boundary.to_crs("EPSG:4326")
        union = boundary_wgs84.geometry.union_all()

        inside = union.covers(point)

        if scenario["category"] == "outside_district":
            if inside:
                raise RuntimeError(
                    f"{scenario['scenario_id']} is labeled "
                    f"outside_district but its point is inside the boundary."
                )
        else:
            if not inside:
                raise RuntimeError(
                    f"{scenario['scenario_id']} should be inside the "
                    f"Woodlands boundary but is outside."
                )


def validate_category_counts(
    scenarios: list[dict],
) -> None:
    """Validate the intended 30-scenario allocation."""

    from collections import Counter

    counts = Counter(
        scenario["category"]
        for scenario in scenarios
    )

    for category, expected in TARGET_COUNTS.items():
        actual = counts.get(category, 0)

        if actual != expected:
            raise RuntimeError(
                f"Category '{category}': expected {expected}, "
                f"generated {actual}."
            )

# GENERATION
def generate_scenarios() -> list[dict]:
    print("PERSON B — 30-SCENARIO DRAFT GENERATOR")
    print()
    print("Loading frozen AED dataset...")

    all_aeds = load_frozen_aed_dataset(AED_DATASET)

    print(f"Loaded {len(all_aeds):,} frozen AED records.")
    print()
    print("Loading frozen study boundary...")

    boundary = load_frozen_boundary(BOUNDARY_PATH)

    print(f"Boundary CRS: {boundary.crs}")

    study_aeds = restrict_to_study_area(
        all_aeds,
        boundary,
    )

    print(
        f"AEDs inside frozen Woodlands boundary: "
        f"{len(study_aeds):,}"
    )

    print()

    # DATA AVAILABILITY CHECK
    unknown_hours_count = int(
        study_aeds.apply(is_blank_hours, axis=1).sum()
    )

    print("Checking scenario strata against frozen data...")
    print(
        f"Woodlands AEDs with blank OPERATING_HOURS: "
        f"{unknown_hours_count}"
    )

    if unknown_hours_count == 0:
        print(
            "NOTE: 'unknown_hours' is unavailable inside the frozen "
            "Woodlands study area."
        )
        print(
            "The script will NOT invent unknown-hours AEDs."
        )

    print()

    scenarios: list[dict] = []

    used_ids: set[str] = set()

    # 1. NORMAL DAYTIME — 4
    print("Generating 4 normal_daytime scenarios...")

    rows = select_distinct_records(
        study_aeds,
        predicate=lambda r: not is_closed_schedule(r)
        and not is_blank_hours(r),
        count=4,
        used_ids=used_ids,
        seed_offset=10,
    )

    for i, (row, dt) in enumerate(
        zip(rows, NORMAL_TIMES),
        start=1,
    ):
        scenario_id = f"s{i:02d}"

        scenarios.append(
            make_inside_scenario(
                scenario_id,
                "normal_daytime",
                row,
                dt,
                "AED record inside Woodlands; ordinary daytime query.",
            )
        )

        used_ids.add(clean_text(row.get("AED_ID")))

    # 2. AFTER HOURS — 3
    print("Generating 3 after_hours scenarios...")

    rows = select_distinct_records(
        study_aeds,
        predicate=lambda r: not is_blank_hours(r),
        count=3,
        used_ids=used_ids,
        seed_offset=20,
    )

    start = len(scenarios) + 1

    for i, (row, dt) in enumerate(
        zip(rows, AFTER_HOURS_TIMES),
        start=start,
    ):
        scenario_id = f"s{i:02d}"

        scenarios.append(
            make_inside_scenario(
                scenario_id,
                "after_hours",
                row,
                dt,
                "AED record inside Woodlands; late-evening query.",
            )
        )

        used_ids.add(clean_text(row.get("AED_ID")))

    # 3. BOUNDARY TIME — 3
    print("Generating 3 boundary_time scenarios...")

    rows = select_distinct_records(
        study_aeds,
        predicate=lambda r: not is_blank_hours(r),
        count=3,
        used_ids=used_ids,
        seed_offset=30,
    )

    start = len(scenarios) + 1

    for i, (row, dt) in enumerate(
        zip(rows, BOUNDARY_TIMES),
        start=start,
    ):
        scenario_id = f"s{i:02d}"

        scenarios.append(
            make_inside_scenario(
                scenario_id,
                "boundary_time",
                row,
                dt,
                "AED record inside Woodlands; query at a schedule boundary time.",
            )
        )

        used_ids.add(clean_text(row.get("AED_ID")))

    # 4. CLOSED AED — 3
    print("Generating 3 closed_aed scenarios...")

    closed_candidates = study_aeds[
        study_aeds.apply(is_closed_schedule, axis=1)
    ]

    if len(closed_candidates) < 3:
        raise RuntimeError(
            "Fewer than 3 AED records with explicit 'Closed' schedule "
            "inside Woodlands."
        )

    rows = select_distinct_records(
        study_aeds,
        predicate=lambda r: is_closed_schedule(r),
        count=3,
        used_ids=used_ids,
        seed_offset=40,
    )

    start = len(scenarios) + 1

    for i, (row, dt) in enumerate(
        zip(rows, CLOSED_TIMES),
        start=start,
    ):
        scenario_id = f"s{i:02d}"

        scenarios.append(
            make_inside_scenario(
                scenario_id,
                "closed_aed",
                row,
                dt,
                "AED record has an explicit recorded Closed schedule.",
            )
        )

        used_ids.add(clean_text(row.get("AED_ID")))

    # 5. UNKNOWN HOURS — 0
    print("Generating 0 unknown_hours scenarios...")
    print(
        "Skipped: no blank OPERATING_HOURS records exist inside "
        "the frozen Woodlands boundary."
    )

    # 6. RELATIONAL LOCATION — 3
    print("Generating 3 relational_location scenarios...")

    rows = select_distinct_records(
        study_aeds,
        predicate=lambda r: has_relational_language(r),
        count=3,
        used_ids=used_ids,
        seed_offset=60,
    )

    start = len(scenarios) + 1

    for i, (row, dt) in enumerate(
        zip(rows, RELATIONAL_TIMES),
        start=start,
    ):
        scenario_id = f"s{i:02d}"

        scenarios.append(
            make_inside_scenario(
                scenario_id,
                "relational_location",
                row,
                dt,
                "AED location description contains relational language "
                "(e.g. near, beside, opposite, behind).",
            )
        )

        used_ids.add(clean_text(row.get("AED_ID")))

    # 7. MISSING FLOOR — 2
    print("Generating 2 missing_floor scenarios...")

    rows = select_distinct_records(
        study_aeds,
        predicate=lambda r: has_missing_floor(r),
        count=2,
        used_ids=used_ids,
        seed_offset=70,
    )

    start = len(scenarios) + 1

    for i, (row, dt) in enumerate(
        zip(rows, MISSING_FLOOR_TIMES),
        start=start,
    ):
        scenario_id = f"s{i:02d}"

        scenarios.append(
            make_inside_scenario(
                scenario_id,
                "missing_floor",
                row,
                dt,
                "AED record has missing floor-level information.",
            )
        )

        used_ids.add(clean_text(row.get("AED_ID")))

    # 8. MULTIPLE CANDIDATE AEDs — 3
    print("Generating 3 multiple_candidate_aeds scenarios...")

    # We select AEDs from buildings with multiple AED records where possible.
    building_counts = (
        study_aeds["BUILDING_NAME"]
        .fillna("")
        .astype(str)
        .str.strip()
        .value_counts()
    )

    multi_buildings = set(
        building_counts[building_counts >= 2].index
    )

    rows = select_distinct_records(
        study_aeds,
        predicate=lambda r: (
            building_name(r) in multi_buildings
            and building_name(r) != ""
        ),
        count=3,
        used_ids=used_ids,
        seed_offset=80,
    )

    start = len(scenarios) + 1

    for i, (row, dt) in enumerate(
        zip(rows, MULTIPLE_CANDIDATE_TIMES),
        start=start,
    ):
        scenario_id = f"s{i:02d}"

        scenarios.append(
            make_inside_scenario(
                scenario_id,
                "multiple_candidate_aeds",
                row,
                dt,
                "Selected from a building containing multiple AED records; "
                "candidate competition must be determined by the routing system.",
            )
        )

        used_ids.add(clean_text(row.get("AED_ID")))

    # 9. NO FEASIBLE AED — 3
    print("Generating 3 no_feasible_aed scenarios...")

    # IMPORTANT:
    # We deliberately DO NOT label these scenarios as actually having no
    # feasible AED. They are merely candidate locations/times selected to
    # stress that condition.

    # Person C must independently determine whether they really have zero
    # feasible AEDs after seeing the scenario.

    rows = select_distinct_records(
        study_aeds,
        predicate=lambda r: not is_blank_hours(r),
        count=3,
        used_ids=used_ids,
        seed_offset=90,
    )

    start = len(scenarios) + 1

    for i, (row, dt) in enumerate(
        zip(rows, NO_FEASIBLE_TIMES),
        start=start,
    ):
        scenario_id = f"s{i:02d}"

        scenarios.append(
            make_inside_scenario(
                scenario_id,
                "no_feasible_aed",
                row,
                dt,
                "Candidate stress-test location/time; final feasibility "
                "must be independently determined by Person C.",
            )
        )

        used_ids.add(clean_text(row.get("AED_ID")))

    # 10. OUTSIDE DISTRICT — 3
    print("Generating 3 outside_district scenarios...")

    outside_points = make_outside_points(
        boundary,
        count=3,
    )

    start = len(scenarios) + 1

    for i, (point, dt) in enumerate(
        zip(outside_points, OUTSIDE_DISTRICT_TIMES),
        start=start,
    ):
        scenario_id = f"s{i:02d}"

        scenarios.append(
            make_outside_scenario(
                scenario_id,
                "outside_district",
                point,
                dt,
                "Point deliberately generated just outside the frozen "
                "Woodlands boundary.",
            )
        )

    # 11. BASELINE SYSTEM DISAGREEMENT — 3
    print("Generating 3 baseline_system_disagreement scenarios...")

    rows = select_distinct_records(
        study_aeds,
        predicate=lambda r: not is_blank_hours(r),
        count=3,
        used_ids=used_ids,
        seed_offset=110,
    )

    start = len(scenarios) + 1

    for i, (row, dt) in enumerate(
        zip(rows, BASELINE_DISAGREEMENT_TIMES),
        start=start,
    ):
        scenario_id = f"s{i:02d}"

        scenarios.append(
            make_inside_scenario(
                scenario_id,
                "baseline_system_disagreement",
                row,
                dt,
                "Candidate comparison case for later baseline-vs-system "
                "evaluation; disagreement is NOT asserted here.",
            )
        )

        used_ids.add(clean_text(row.get("AED_ID")))

    # FINAL SORT
    scenarios.sort(
        key=lambda x: x["scenario_id"]
    )

    # VALIDATE
    validate_category_counts(scenarios)
    validate_scenarios(scenarios, boundary)

    # OUTPUT
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_document = {
        "metadata": {
            "generator": "Person B — 30-Scenario Draft Generator",
            "study_area": "Woodlands",
            "planning_area_code": "WD",
            "source_aed_dataset": str(AED_DATASET),
            "source_boundary": str(BOUNDARY_PATH),
            "total_frozen_aed_records": int(len(all_aeds)),
            "study_area_aed_records": int(len(study_aeds)),
            "target_scenario_count": TARGET_SCENARIO_COUNT,
            "random_seed": RANDOM_SEED,
            "status": "draft",
            "feasibility_labeled": False,
            "true_feasible_ids_assigned": False,
        },

        "strata": {
            "requested": STRATA,
            "target_counts": TARGET_COUNTS,
        },

        "unavailable_strata": {
            "unknown_hours": {
                "reason": (
                    "No AED records inside the frozen Woodlands study "
                    "boundary have blank OPERATING_HOURS."
                ),
                "available_records": unknown_hours_count,
                "generated_scenarios": 0,
                "action": (
                    "No synthetic records were invented. The two originally "
                    "requested unknown-hours scenarios were redistributed "
                    "to other valid strata."
                ),
            }
        },

        "scenarios": scenarios,
    }

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            output_document,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # SUMMARY
    from collections import Counter

    counts = Counter(
        s["category"]
        for s in scenarios
    )

    print()
    print("=" * 60)
    print("30-SCENARIO DRAFT GENERATION COMPLETE")
    print("=" * 60)
    print()
    print(f"Total scenarios: {len(scenarios)}")
    print()

    print("Category counts:")
    for category in STRATA:
        print(
            f"  {category:<32} "
            f"{counts.get(category, 0)}"
        )

    print()
    print("Unavailable strata:")
    print(
        "  unknown_hours: 0 scenarios "
        f"(matching Woodlands AEDs: {unknown_hours_count})"
    )

    print()
    print(f"Output: {OUTPUT_PATH}")
    print()
    print("IMPORTANT:")
    print("  - These are DRAFT scenarios.")
    print("  - No feasibility labels were assigned.")
    print("  - true_feasible_aed_ids were NOT added.")
    print("  - Person C must label independently.")
    print("  - Person A must perform graph sanity checks.")
    print("  - The team must adjudicate disagreements.")
    print()
    print("Do NOT rename this file to ground_truth.json yet.")

    return scenarios


def main() -> None:
    generate_scenarios()


if __name__ == "__main__":
    main()