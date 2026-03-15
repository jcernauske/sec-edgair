"""Core corruption engine — generates adversarial data across all 10 DQ dimensions.

The injector ONLY knows about raw zone physical schemas. It has NO knowledge
of DQ rules, tests, or scorecards. This information barrier is by design.
"""

from __future__ import annotations

import datetime
import random
import string
from dataclasses import dataclass, field

from src.infra.chaos_monkey.config import DQ_DIMENSIONS, MIN_PER_DIMENSION


@dataclass
class Corruption:
    """A single corruption injection record."""

    corruption_id: str
    dimension: str
    strategy: str
    description: str
    field_name: str
    original_value: str | None
    corrupted_value: str | None
    row_identifier: str
    expected_detection: str


@dataclass
class InjectionPlan:
    """Plan for all corruptions in a single run."""

    corruptions: list[Corruption] = field(default_factory=list)
    corrupted_rows: list[dict] = field(default_factory=list)

    @property
    def dimension_coverage(self) -> dict[str, bool]:
        dims_hit = {c.dimension for c in self.corruptions}
        return {d: d in dims_hit for d in DQ_DIMENSIONS}

    @property
    def all_dimensions_covered(self) -> bool:
        return all(self.dimension_coverage.values())


def generate_corruptions(
    source_rows: list[dict],
    injection_rate: float,
    seed: int | None = None,
) -> InjectionPlan:
    """Generate corrupted rows covering all 10 DQ dimensions.

    Args:
        source_rows: Clean rows from the raw zone table.
        injection_rate: Fraction of source rows to corrupt (0.05-0.10).
        seed: Random seed for reproducibility.

    Returns:
        InjectionPlan with corrupted rows and corruption manifest entries.
    """
    rng = random.Random(seed)
    target_count = max(
        int(len(source_rows) * injection_rate),
        len(DQ_DIMENSIONS) * MIN_PER_DIMENSION,
    )

    plan = InjectionPlan()
    corruption_counter = 0

    # Allocate corruptions per dimension — guarantee minimum coverage,
    # then distribute remaining budget randomly
    budget = _allocate_budget(target_count, rng)

    for dimension, count in budget.items():
        generator = _DIMENSION_GENERATORS[dimension]
        for _ in range(count):
            corruption_counter += 1
            cid = f"CHAOS-{corruption_counter:05d}"
            row = rng.choice(source_rows).copy()
            row_id = f"shadow-row-{corruption_counter:05d}"

            corruption = generator(row, cid, row_id, rng)
            plan.corruptions.append(corruption)
            plan.corrupted_rows.append(row)

    return plan


def _allocate_budget(target_count: int, rng: random.Random) -> dict[str, int]:
    """Distribute corruption budget across dimensions."""
    budget = {d: MIN_PER_DIMENSION for d in DQ_DIMENSIONS}
    remaining = target_count - sum(budget.values())
    if remaining > 0:
        for _ in range(remaining):
            dim = rng.choice(DQ_DIMENSIONS)
            budget[dim] += 1
    return budget


# ---------------------------------------------------------------------------
# Dimension-specific generators
# ---------------------------------------------------------------------------
# Each generator mutates the row dict in-place and returns a Corruption record.


def _gen_completeness(row: dict, cid: str, row_id: str, rng: random.Random) -> Corruption:
    """Null out a required field."""
    required_fields = ["cik", "entity_name", "taxonomy", "concept", "unit",
                       "end_date", "val", "accession_number", "form",
                       "filed_date", "ingested_at", "source_url",
                       "source_method", "load_date"]
    target = rng.choice(required_fields)
    original = str(row.get(target))
    row[target] = None
    return Corruption(
        corruption_id=cid, dimension="completeness",
        strategy="null_required_field",
        description=f"Set {target} to NULL on injected row",
        field_name=target, original_value=original, corrupted_value=None,
        row_identifier=row_id,
        expected_detection=f"Any DQ rule checking NOT NULL on {target}",
    )


def _gen_validity(row: dict, cid: str, row_id: str, rng: random.Random) -> Corruption:
    """Insert invalid values in constrained fields."""
    strategies = [
        ("fiscal_period", "Q9", "Invalid fiscal period"),
        ("form", "99-Z", "Invalid SEC form type"),
        ("unit", "", "Empty unit string"),
        ("taxonomy", "fake-gaap-2099", "Invalid taxonomy"),
        ("source_method", "", "Empty source method"),
    ]
    target, bad_val, desc = rng.choice(strategies)
    original = str(row.get(target))
    row[target] = bad_val
    return Corruption(
        corruption_id=cid, dimension="validity",
        strategy="invalid_field_value",
        description=f"{desc}: {target}={bad_val!r}",
        field_name=target, original_value=original, corrupted_value=bad_val,
        row_identifier=row_id,
        expected_detection=f"Any DQ rule validating allowed values for {target}",
    )


def _gen_uniqueness(row: dict, cid: str, row_id: str, rng: random.Random) -> Corruption:
    """Create exact duplicate rows or duplicate keys."""
    # Full row copy — row dict is already a copy of an existing row
    # Don't mutate anything; the duplicate IS the corruption
    return Corruption(
        corruption_id=cid, dimension="uniqueness",
        strategy="full_row_duplicate",
        description=f"Exact copy of existing row (CIK {row.get('cik')}, concept {row.get('concept')})",
        field_name="*", original_value="existing row", corrupted_value="exact duplicate",
        row_identifier=row_id,
        expected_detection="Any uniqueness or duplicate detection DQ rule",
    )


def _gen_consistency(row: dict, cid: str, row_id: str, rng: random.Random) -> Corruption:
    """Create contradictory field combinations."""
    strategies = rng.choice(["date_inversion", "fy_mismatch"])
    if strategies == "date_inversion":
        # start_date after end_date
        row["start_date"] = datetime.date(2099, 12, 31)
        row["end_date"] = datetime.date(2000, 1, 1)
        return Corruption(
            corruption_id=cid, dimension="consistency",
            strategy="date_inversion",
            description="start_date (2099-12-31) > end_date (2000-01-01)",
            field_name="start_date,end_date",
            original_value="valid date range", corrupted_value="inverted range",
            row_identifier=row_id,
            expected_detection="Any DQ rule checking start_date <= end_date",
        )
    else:
        # fiscal_year doesn't match end_date year
        row["fiscal_year"] = 1999
        row["end_date"] = datetime.date(2024, 12, 31)
        return Corruption(
            corruption_id=cid, dimension="consistency",
            strategy="fiscal_year_mismatch",
            description="fiscal_year=1999 but end_date=2024-12-31",
            field_name="fiscal_year,end_date",
            original_value="matching year", corrupted_value="mismatched year",
            row_identifier=row_id,
            expected_detection="Any DQ rule checking fiscal_year consistency with end_date",
        )


def _gen_accuracy(row: dict, cid: str, row_id: str, rng: random.Random) -> Corruption:
    """Plausible but wrong values."""
    strategies = rng.choice(["tiny_revenue", "negative_absolute"])
    if strategies == "tiny_revenue":
        original = str(row.get("val"))
        row["val"] = 1.0  # $1 revenue for a Fortune 500
        return Corruption(
            corruption_id=cid, dimension="accuracy",
            strategy="implausible_value",
            description=f"Set val to $1 (was {original})",
            field_name="val", original_value=original, corrupted_value="1.0",
            row_identifier=row_id,
            expected_detection="Any DQ rule checking value plausibility or statistical outliers",
        )
    else:
        original = str(row.get("val"))
        row["val"] = -abs(float(original)) if original and original != "None" else -999.0
        return Corruption(
            corruption_id=cid, dimension="accuracy",
            strategy="negative_absolute_metric",
            description=f"Negated val to {row['val']} (was {original})",
            field_name="val", original_value=original, corrupted_value=str(row["val"]),
            row_identifier=row_id,
            expected_detection="Any DQ rule checking for unexpected negative values",
        )


def _gen_reasonableness(row: dict, cid: str, row_id: str, rng: random.Random) -> Corruption:
    """Extreme outliers that no sane data should contain."""
    strategies = rng.choice(["extreme_val", "ancient_year", "zero_cik"])
    if strategies == "extreme_val":
        original = str(row.get("val"))
        row["val"] = 999_999_999_999_999.0
        return Corruption(
            corruption_id=cid, dimension="reasonableness",
            strategy="extreme_outlier_value",
            description=f"Set val to 999,999,999,999,999 (was {original})",
            field_name="val", original_value=original,
            corrupted_value="999999999999999.0",
            row_identifier=row_id,
            expected_detection="Any DQ rule checking value bounds or statistical reasonableness",
        )
    elif strategies == "ancient_year":
        original = str(row.get("fiscal_year"))
        row["fiscal_year"] = 1850
        return Corruption(
            corruption_id=cid, dimension="reasonableness",
            strategy="impossible_fiscal_year",
            description=f"Set fiscal_year to 1850 (was {original})",
            field_name="fiscal_year", original_value=original, corrupted_value="1850",
            row_identifier=row_id,
            expected_detection="Any DQ rule checking fiscal_year range",
        )
    else:
        original = str(row.get("cik"))
        row["cik"] = 0
        return Corruption(
            corruption_id=cid, dimension="reasonableness",
            strategy="zero_cik",
            description=f"Set cik to 0 (was {original})",
            field_name="cik", original_value=original, corrupted_value="0",
            row_identifier=row_id,
            expected_detection="Any DQ rule checking cik > 0 or valid CIK range",
        )


def _gen_freshness(row: dict, cid: str, row_id: str, rng: random.Random) -> Corruption:
    """Stale or future timestamps."""
    strategies = rng.choice(["future_ingest", "ancient_filed"])
    if strategies == "future_ingest":
        original = str(row.get("ingested_at"))
        row["ingested_at"] = datetime.datetime(2099, 1, 1, tzinfo=datetime.timezone.utc)
        return Corruption(
            corruption_id=cid, dimension="freshness",
            strategy="future_timestamp",
            description=f"Set ingested_at to 2099-01-01 (was {original})",
            field_name="ingested_at", original_value=original,
            corrupted_value="2099-01-01T00:00:00Z",
            row_identifier=row_id,
            expected_detection="Any DQ rule checking ingested_at is not in the future",
        )
    else:
        original = str(row.get("filed_date"))
        row["filed_date"] = datetime.date(1900, 1, 1)
        return Corruption(
            corruption_id=cid, dimension="freshness",
            strategy="ancient_timestamp",
            description=f"Set filed_date to 1900-01-01 (was {original})",
            field_name="filed_date", original_value=original,
            corrupted_value="1900-01-01",
            row_identifier=row_id,
            expected_detection="Any DQ rule checking filed_date recency or range",
        )


def _gen_volume(row: dict, cid: str, row_id: str, rng: random.Random) -> Corruption:
    """Row count anomaly — burst of rows for a single CIK.

    The row is marked as a volume-spike injection. When many of these
    are injected for the same CIK, it creates a detectable volume anomaly.
    """
    # Pick a CIK and stamp it — the volume spike comes from many of these
    # being allocated to the same CIK by the budget allocator
    cik = row.get("cik", 320193)
    row["cik"] = cik  # Keep same CIK to cluster the burst
    # Give it a unique concept to inflate the count
    row["concept"] = f"chaos:VolumeSpike{rng.randint(1, 99999)}"
    return Corruption(
        corruption_id=cid, dimension="volume",
        strategy="volume_spike",
        description=f"Burst injection for CIK {cik} with fake concept",
        field_name="concept", original_value=row.get("concept"),
        corrupted_value=row["concept"],
        row_identifier=row_id,
        expected_detection="Any DQ rule checking row count bounds or volume anomalies",
    )


def _gen_referential_integrity(row: dict, cid: str, row_id: str, rng: random.Random) -> Corruption:
    """Orphan keys — references that point to nothing."""
    strategies = rng.choice(["fake_cik", "fake_accession"])
    if strategies == "fake_cik":
        original = str(row.get("cik"))
        row["cik"] = 9999999
        return Corruption(
            corruption_id=cid, dimension="referential_integrity",
            strategy="orphan_cik",
            description=f"Set cik to 9999999 (nonexistent, was {original})",
            field_name="cik", original_value=original, corrupted_value="9999999",
            row_identifier=row_id,
            expected_detection="Any DQ rule checking CIK exists in entity_mappings or known CIK list",
        )
    else:
        original = str(row.get("accession_number"))
        fake = f"FAKE-{rng.randint(100, 999)}-{rng.randint(10000, 99999)}"
        row["accession_number"] = fake
        return Corruption(
            corruption_id=cid, dimension="referential_integrity",
            strategy="fake_accession_number",
            description=f"Set accession_number to {fake} (was {original})",
            field_name="accession_number", original_value=original,
            corrupted_value=fake,
            row_identifier=row_id,
            expected_detection="Any DQ rule validating accession_number format or existence",
        )


def _gen_coverage(row: dict, cid: str, row_id: str, rng: random.Random) -> Corruption:
    """Create rows that introduce coverage gaps."""
    strategies = rng.choice(["no_annual", "no_usd"])
    if strategies == "no_annual":
        # A CIK with only quarterly data (no annual)
        row["cik"] = 8888888  # Fake CIK
        row["entity_name"] = "CHAOS_COVERAGE_TEST_CORP"
        row["fiscal_period"] = "Q1"  # Only quarterly, never annual
        return Corruption(
            corruption_id=cid, dimension="coverage",
            strategy="missing_annual_filings",
            description="Injected CIK 8888888 with only quarterly filings (no annual)",
            field_name="cik,fiscal_period",
            original_value="mixed periods", corrupted_value="Q1 only",
            row_identifier=row_id,
            expected_detection="Any DQ rule checking for expected period type coverage per entity",
        )
    else:
        # A concept with non-USD unit only
        row["unit"] = "FAKE_CURRENCY"
        row["concept"] = "chaos:NoCoverageMetric"
        return Corruption(
            corruption_id=cid, dimension="coverage",
            strategy="non_standard_unit",
            description=f"Injected concept with unit=FAKE_CURRENCY (no USD)",
            field_name="unit,concept",
            original_value="USD", corrupted_value="FAKE_CURRENCY",
            row_identifier=row_id,
            expected_detection="Any DQ rule checking unit distribution or expected unit coverage",
        )


# Map dimension names to their generator functions
_DIMENSION_GENERATORS = {
    "completeness": _gen_completeness,
    "validity": _gen_validity,
    "uniqueness": _gen_uniqueness,
    "consistency": _gen_consistency,
    "accuracy": _gen_accuracy,
    "reasonableness": _gen_reasonableness,
    "freshness": _gen_freshness,
    "volume": _gen_volume,
    "referential_integrity": _gen_referential_integrity,
    "coverage": _gen_coverage,
}
