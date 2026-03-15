"""Negative verification: prove incorrect data is ABSENT from our pipeline.

Complement to verify.py (positive verification). Runs against real Iceberg
tables and asserts things that should NOT exist: duplicate grains, superseded
facts, null business terms, wrong units, orphan ratios, etc.

Spec: docs/specs/infra-semantic-dq-and-negative-testing.md (section 3)
"""
import sys
from collections import Counter

sys.path.insert(0, ".")
from src.infra.iceberg_setup import get_catalog, read_with_duckdb


# ---------------------------------------------------------------------------
# Load all tables
# ---------------------------------------------------------------------------
def load_tables():
    """Load all tables needed for negative verification."""
    base_catalog = get_catalog(
        "data/raw/iceberg_warehouse", "data/catalog/catalog.db"
    )
    cons_catalog = get_catalog(
        "data/consumable/iceberg_warehouse", "data/catalog/catalog.db"
    )

    tables = {
        "conformed_facts": read_with_duckdb(
            base_catalog.load_table("base.conformed_facts")
        ),
        "financial_facts": read_with_duckdb(
            base_catalog.load_table("base.financial_facts")
        ),
        "company_financials": read_with_duckdb(
            cons_catalog.load_table("consumable.company_financials")
        ),
        "financial_ratios": read_with_duckdb(
            cons_catalog.load_table("consumable.financial_ratios")
        ),
        "peer_comparison": read_with_duckdb(
            cons_catalog.load_table("consumable.peer_comparison")
        ),
    }
    return tables


# ---------------------------------------------------------------------------
# Per-share business term IDs
# ---------------------------------------------------------------------------
PER_SHARE_BTS = {"BT-044", "BT-045", "BT-046"}


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------
def check_no_duplicate_grains_company_financials(tables):
    """Check 1: No duplicate grains in company_financials."""
    rows = tables["company_financials"]
    grains = [
        (r["cik"], r["business_term_id"], r["fiscal_year"], r["fiscal_period"])
        for r in rows
    ]
    counts = Counter(grains)
    dupes = {g: c for g, c in counts.items() if c > 1}

    if not dupes:
        return True, f"No duplicate grains in company_financials ({len(rows)} rows, {len(counts)} unique grains)"
    else:
        detail = "; ".join(
            f"cik={g[0]}, bt={g[1]}, fy={g[2]}, fp={g[3]} (x{c})"
            for g, c in list(dupes.items())[:5]
        )
        return False, f"Found {len(dupes)} duplicate grains in company_financials: {detail}"


def check_no_superseded_facts(tables):
    """Check 2: No superseded facts in conformed_facts."""
    conformed = tables["conformed_facts"]
    financial = tables["financial_facts"]

    # Build lookup of superseded fact IDs
    superseded_ids = {
        f["fact_id"]
        for f in financial
        if f.get("is_superseded") is True
    }

    # Check if any conformed_facts reference a superseded source fact
    leaked = [
        r for r in conformed
        if r["source_fact_id"] in superseded_ids
    ]

    if not leaked:
        return True, f"No superseded facts leaked to conformed_facts (checked {len(conformed)} rows against {len(superseded_ids)} superseded facts)"
    else:
        detail = "; ".join(
            f"conformed_id={r['conformed_id']}, source_fact_id={r['source_fact_id']}"
            for r in leaked[:5]
        )
        return False, f"Found {len(leaked)} superseded facts in conformed_facts: {detail}"


def check_no_null_business_term(tables):
    """Check 3: No unmapped facts (null BT) in conformed_facts."""
    conformed = tables["conformed_facts"]
    null_bt = [r for r in conformed if r.get("business_term_id") is None]

    if not null_bt:
        return True, f"No null business_term_id in conformed_facts ({len(conformed)} rows checked)"
    else:
        return False, f"Found {len(null_bt)} rows with null business_term_id in conformed_facts"


def check_no_null_fiscal_year(tables):
    """Check 4: No null fiscal years in conformed_facts."""
    conformed = tables["conformed_facts"]
    null_fy = [r for r in conformed if r.get("fiscal_year") is None]

    if not null_fy:
        return True, f"No null fiscal_year in conformed_facts ({len(conformed)} rows checked)"
    else:
        return False, f"Found {len(null_fy)} rows with null fiscal_year in conformed_facts"


def check_no_wrong_units(tables):
    """Check 5: No wrong-unit values in conformed_facts.

    Per-share BTs (BT-044, 045, 046) should have unit='USD/shares'.
    All other BTs should have unit='USD'.
    """
    conformed = tables["conformed_facts"]
    wrong = []

    for r in conformed:
        bt = r.get("business_term_id")
        unit = r.get("unit")
        if bt in PER_SHARE_BTS:
            if unit != "USD/shares":
                wrong.append((bt, unit, r.get("conformed_id")))
        else:
            if unit != "USD":
                wrong.append((bt, unit, r.get("conformed_id")))

    if not wrong:
        return True, f"No wrong-unit values in conformed_facts ({len(conformed)} rows checked)"
    else:
        detail = "; ".join(
            f"bt={w[0]}, unit={w[1]}, id={w[2]}"
            for w in wrong[:5]
        )
        return False, f"Found {len(wrong)} wrong-unit values in conformed_facts: {detail}"


def check_no_fiscal_year_collisions(tables):
    """Check 6: No fiscal year collisions in company_financials.

    For a given (cik, business_term_id, period_end_date, fiscal_period),
    fiscal_year should be unique (no two different fiscal_years for the
    same company + metric + period_end_date + fiscal_period).
    """
    rows = tables["company_financials"]
    groups: dict[tuple, set] = {}

    for r in rows:
        key = (r["cik"], r["business_term_id"], str(r["period_end_date"]), r["fiscal_period"])
        fy = r["fiscal_year"]
        if key not in groups:
            groups[key] = set()
        groups[key].add(fy)

    collisions = {k: v for k, v in groups.items() if len(v) > 1}

    if not collisions:
        return True, f"No fiscal year collisions in company_financials ({len(groups)} grain groups checked)"
    else:
        detail = "; ".join(
            f"cik={k[0]}, bt={k[1]}, end={k[2]}, fp={k[3]} -> FYs={sorted(v)}"
            for k, v in list(collisions.items())[:5]
        )
        return False, f"Found {len(collisions)} fiscal year collisions in company_financials: {detail}"


def check_no_orphan_ratios(tables):
    """Check 7: No orphan ratios in financial_ratios.

    Every (cik, fiscal_year, fiscal_period, numerator_bt_id) and
    (cik, fiscal_year, fiscal_period, denominator_bt_id) should exist
    in company_financials.
    """
    ratios = tables["financial_ratios"]
    cf = tables["company_financials"]

    # Build lookup set of (cik, business_term_id, fiscal_year, fiscal_period)
    cf_grains = {
        (r["cik"], r["business_term_id"], r["fiscal_year"], r["fiscal_period"])
        for r in cf
    }

    orphan_numerators = []
    orphan_denominators = []

    for r in ratios:
        num_key = (r["cik"], r["numerator_bt_id"], r["fiscal_year"], r["fiscal_period"])
        den_key = (r["cik"], r["denominator_bt_id"], r["fiscal_year"], r["fiscal_period"])
        if num_key not in cf_grains:
            orphan_numerators.append(r)
        if den_key not in cf_grains:
            orphan_denominators.append(r)

    total_orphans = len(orphan_numerators) + len(orphan_denominators)

    if total_orphans == 0:
        return True, f"No orphan ratios in financial_ratios ({len(ratios)} ratios, all numerators and denominators found in company_financials)"
    else:
        parts = []
        if orphan_numerators:
            parts.append(f"{len(orphan_numerators)} orphan numerators")
        if orphan_denominators:
            parts.append(f"{len(orphan_denominators)} orphan denominators")
        return False, f"Found {', '.join(parts)} in financial_ratios"


def check_row_count_alignment(tables):
    """Check 8: Row count alignment between company_financials and conformed_facts."""
    cf_count = len(tables["company_financials"])
    base_count = len(tables["conformed_facts"])

    if cf_count == base_count:
        return True, f"Row count aligned: company_financials ({cf_count}) = conformed_facts ({base_count})"
    else:
        diff = cf_count - base_count
        direction = "more" if diff > 0 else "fewer"
        return False, f"Row count mismatch: company_financials ({cf_count}) vs conformed_facts ({base_count}) -- {abs(diff)} {direction} rows"


def check_no_duplicate_peer_rankings(tables):
    """Check 9: No duplicate peer rankings in peer_comparison."""
    rows = tables["peer_comparison"]
    grains = [
        (r["cik"], r["metric_id"], r["fiscal_year"], r["fiscal_period"], r["metric_source"])
        for r in rows
    ]
    counts = Counter(grains)
    dupes = {g: c for g, c in counts.items() if c > 1}

    if not dupes:
        return True, f"No duplicate peer rankings in peer_comparison ({len(rows)} rows, {len(counts)} unique grains)"
    else:
        detail = "; ".join(
            f"cik={g[0]}, metric={g[1]}, fy={g[2]}, fp={g[3]}, src={g[4]} (x{c})"
            for g, c in list(dupes.items())[:5]
        )
        return False, f"Found {len(dupes)} duplicate peer rankings in peer_comparison: {detail}"


def check_no_cross_zone_grain_violations(tables):
    """Check 10: No cross-zone grain violations.

    Every (cik, business_term_id, fiscal_year, fiscal_period) in
    company_financials should exist in conformed_facts.
    """
    cf = tables["company_financials"]
    conformed = tables["conformed_facts"]

    conformed_grains = {
        (r["cik"], r["business_term_id"], r["fiscal_year"], r["fiscal_period"])
        for r in conformed
    }

    missing = []
    for r in cf:
        grain = (r["cik"], r["business_term_id"], r["fiscal_year"], r["fiscal_period"])
        if grain not in conformed_grains:
            missing.append(grain)

    if not missing:
        return True, f"No cross-zone grain violations ({len(cf)} company_financials grains all found in conformed_facts)"
    else:
        detail = "; ".join(
            f"cik={g[0]}, bt={g[1]}, fy={g[2]}, fp={g[3]}"
            for g in missing[:5]
        )
        return False, f"Found {len(missing)} company_financials grains not in conformed_facts: {detail}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
ALL_CHECKS = [
    ("No duplicate grains in company_financials", check_no_duplicate_grains_company_financials),
    ("No superseded facts in conformed_facts", check_no_superseded_facts),
    ("No unmapped facts (null BT) in conformed_facts", check_no_null_business_term),
    ("No null fiscal years in conformed_facts", check_no_null_fiscal_year),
    ("No wrong-unit values in conformed_facts", check_no_wrong_units),
    ("No fiscal year collisions in company_financials", check_no_fiscal_year_collisions),
    ("No orphan ratios in financial_ratios", check_no_orphan_ratios),
    ("Row count alignment (company_financials = conformed_facts)", check_row_count_alignment),
    ("No duplicate peer rankings in peer_comparison", check_no_duplicate_peer_rankings),
    ("No cross-zone grain violations", check_no_cross_zone_grain_violations),
]


def main():
    print("=" * 100)
    print("NEGATIVE VERIFICATION: Proving incorrect data is absent")
    print("=" * 100)
    print()

    print("Loading tables...")
    tables = load_tables()
    print(
        f"  conformed_facts: {len(tables['conformed_facts']):,} rows | "
        f"financial_facts: {len(tables['financial_facts']):,} rows | "
        f"company_financials: {len(tables['company_financials']):,} rows | "
        f"financial_ratios: {len(tables['financial_ratios']):,} rows | "
        f"peer_comparison: {len(tables['peer_comparison']):,} rows"
    )
    print()

    passed = 0
    failed = 0

    for i, (name, check_fn) in enumerate(ALL_CHECKS, 1):
        try:
            ok, detail = check_fn(tables)
        except Exception as e:
            ok = False
            detail = f"Exception: {e}"

        if ok:
            passed += 1
            print(f"  [ OK] {i:2d}. {detail}")
        else:
            failed += 1
            print(f"  [FAIL] {i:2d}. {detail}")

    total = passed + failed
    print()
    print("=" * 100)
    print(f"Results: {passed} pass | {failed} fail | {total} total")
    if failed == 0:
        print("ALL NEGATIVE CHECKS PASSED")
    else:
        print("NEGATIVE VERIFICATION FAILED")
        sys.exit(1)
    print("=" * 100)


if __name__ == "__main__":
    main()
