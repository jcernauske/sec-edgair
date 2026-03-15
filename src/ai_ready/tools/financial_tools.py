"""7 validated tool functions for querying consumable Iceberg financial data.

Each function:
1. Accepts typed parameters
2. Queries in-memory DuckDB data (loaded from Iceberg)
3. Formats numbers via formatters.py
4. Checks anomalies via anomaly_checker.py
5. Returns a structured dict

The data is loaded once and cached. Each tool function runs parameterized
SQL queries against the cached DuckDB tables.
"""

from __future__ import annotations

from src.consumable.company_financials.config import PRIMARY_UNIT
from src.consumable.financial_ratios.config import RATIO_BY_ID, RATIO_DEFINITIONS

from .anomaly_checker import check_anomalies, check_fiscal_alignment
from .db import get_db
from .formatters import format_currency, format_percentage, format_ratio, format_value, format_yoy_pct

# ---------------------------------------------------------------------------
# Metric resolution: support both names ("Revenue") and IDs ("BT-022")
# ---------------------------------------------------------------------------

_METRIC_NAME_TO_ID: dict[str, str] = {}
_METRIC_ID_TO_NAME: dict[str, str] = {}
_RATIO_NAME_TO_ID: dict[str, str] = {}
_RATIO_ID_TO_NAME: dict[str, str] = {}

for _r in RATIO_DEFINITIONS:
    _RATIO_NAME_TO_ID[_r["ratio_name"].lower()] = _r["ratio_id"]
    _RATIO_ID_TO_NAME[_r["ratio_id"]] = _r["ratio_name"]

_PER_SHARE_BT_IDS = {"BT-044", "BT-045", "BT-046"}
_MULTIPLIER_RATIO_IDS = {"RATIO-004", "RATIO-007"}


def _ensure_metric_lookups() -> None:
    """Populate metric name <-> ID lookups from DB data (lazy, once)."""
    if _METRIC_NAME_TO_ID:
        return
    con = get_db()
    try:
        rows = con.execute(
            "SELECT DISTINCT business_term_id, business_term FROM company_financials"
        ).fetchall()
        for bt_id, bt_name in rows:
            if bt_id and bt_name:
                _METRIC_NAME_TO_ID[bt_name.lower()] = bt_id
                _METRIC_ID_TO_NAME[bt_id] = bt_name
    except Exception:
        pass


def _resolve_metric(metric: str) -> tuple[str, str]:
    """Resolve a metric name or ID to (business_term_id, business_term_name)."""
    _ensure_metric_lookups()
    if metric.upper().startswith("BT-"):
        bt_id = metric.upper()
        return bt_id, _METRIC_ID_TO_NAME.get(bt_id, metric)
    bt_id = _METRIC_NAME_TO_ID.get(metric.lower())
    if bt_id:
        return bt_id, _METRIC_ID_TO_NAME.get(bt_id, metric)
    for name, bid in _METRIC_NAME_TO_ID.items():
        if metric.lower() in name:
            return bid, _METRIC_ID_TO_NAME.get(bid, name)
    raise ValueError(f"Unknown metric: '{metric}'. Available metrics: {list(_METRIC_ID_TO_NAME.values())}")


def _resolve_ratio(ratio: str) -> tuple[str, str]:
    """Resolve a ratio name or ID to (ratio_id, ratio_name)."""
    if ratio.upper().startswith("RATIO-"):
        ratio_id = ratio.upper()
        return ratio_id, _RATIO_ID_TO_NAME.get(ratio_id, ratio)
    ratio_id = _RATIO_NAME_TO_ID.get(ratio.lower())
    if ratio_id:
        return ratio_id, _RATIO_ID_TO_NAME.get(ratio_id, ratio)
    for name, rid in _RATIO_NAME_TO_ID.items():
        if ratio.lower() in name:
            return rid, _RATIO_ID_TO_NAME.get(rid, name)
    raise ValueError(f"Unknown ratio: '{ratio}'. Available ratios: {list(_RATIO_ID_TO_NAME.values())}")


def _detect_metric_or_ratio(metric: str) -> tuple[str, str, str]:
    """Detect if a metric refers to company_financials or financial_ratios.

    Returns (source, id, name). Tries exact matches before partial.
    """
    if metric.upper().startswith("RATIO-"):
        ratio_id, ratio_name = _resolve_ratio(metric)
        return "financial_ratios", ratio_id, ratio_name
    if metric.upper().startswith("BT-"):
        bt_id, bt_name = _resolve_metric(metric)
        return "company_financials", bt_id, bt_name

    _ensure_metric_lookups()

    bt_id = _METRIC_NAME_TO_ID.get(metric.lower())
    if bt_id:
        return "company_financials", bt_id, _METRIC_ID_TO_NAME.get(bt_id, metric)
    ratio_id = _RATIO_NAME_TO_ID.get(metric.lower())
    if ratio_id:
        return "financial_ratios", ratio_id, _RATIO_ID_TO_NAME.get(ratio_id, metric)
    for name, bid in _METRIC_NAME_TO_ID.items():
        if metric.lower() in name:
            return "company_financials", bid, _METRIC_ID_TO_NAME.get(bid, name)
    for name, rid in _RATIO_NAME_TO_ID.items():
        if metric.lower() in name:
            return "financial_ratios", rid, _RATIO_ID_TO_NAME.get(rid, name)

    raise ValueError(f"Unknown metric: '{metric}'. Available: {list(_METRIC_ID_TO_NAME.values()) + list(_RATIO_ID_TO_NAME.values())}")


def _format_metric_value(value: float | None, bt_id: str | None = None) -> str:
    """Format a metric value based on its business term ID."""
    if value is None:
        return "N/A"
    if bt_id in _PER_SHARE_BT_IDS:
        return format_value(value, unit="USD/shares")
    unit = PRIMARY_UNIT.get(bt_id, "USD") if bt_id else "USD"
    return format_value(value, unit=unit)


def _format_ratio_value(value: float | None, ratio_id: str | None = None) -> str:
    """Format a ratio value based on its ratio ID."""
    if value is None:
        return "N/A"
    if ratio_id in _MULTIPLIER_RATIO_IDS:
        return format_ratio(value)
    return format_percentage(value)


def _compute_trend_direction(yoy_pcts: list[float]) -> str:
    """Classify a trend from YoY percentage changes."""
    if not yoy_pcts or len(yoy_pcts) < 2:
        return "insufficient_data"
    positive = sum(1 for p in yoy_pcts if p > 0.01)
    negative = sum(1 for p in yoy_pcts if p < -0.01)
    total = len(yoy_pcts)
    if positive > 0 and negative > 0 and min(positive, negative) / total > 0.3:
        return "volatile"
    if positive / total >= 0.7:
        return "growing"
    if negative / total >= 0.7:
        return "declining"
    return "stable"


# ---------------------------------------------------------------------------
# Shared enrichment primitives
# ---------------------------------------------------------------------------


def _fetch_metric_growth(con, ticker: str, bt_id: str, fy: int,
                         fp: str) -> tuple[float | None, float | None, float | None]:
    """Fetch YoY change, YoY pct, and CAGR 5yr from period_over_period.

    Returns (yoy_change, yoy_pct, cagr_5yr).
    """
    yoy_change, yoy_pct, cagr_5yr = None, None, None
    try:
        rows = con.execute(
            """SELECT growth_type, growth_value FROM period_over_period
               WHERE ticker = ? AND business_term_id = ?
                 AND fiscal_year = ? AND fiscal_period = ?
                 AND growth_type IN ('yoy_change', 'yoy_pct_change', 'cagr_5yr')""",
            [ticker, bt_id, fy, fp],
        ).fetchall()
        for gtype, gval in rows:
            if gtype == "yoy_change":
                yoy_change = gval
            elif gtype == "yoy_pct_change":
                yoy_pct = gval
            elif gtype == "cagr_5yr":
                cagr_5yr = gval
    except Exception:
        pass
    return yoy_change, yoy_pct, cagr_5yr


def _fetch_metric_peer_rank(con, ticker: str, metric_id: str, fy: int,
                            fp: str) -> tuple[int | None, float | None, int | None]:
    """Fetch sector rank from peer_comparison for a company_financials metric.

    Returns (sector_rank, sector_percentile, peer_count).
    """
    try:
        row = con.execute(
            """SELECT sector_rank, sector_percentile, peer_count
               FROM peer_comparison
               WHERE ticker = ? AND metric_id = ?
                 AND fiscal_year = ? AND fiscal_period = ?
                 AND metric_source = 'company_financials'""",
            [ticker, metric_id, fy, fp],
        ).fetchone()
        if row:
            return row[0], row[1], row[2]
    except Exception:
        pass
    return None, None, None


def _fetch_ratio_peer_rank(con, ticker: str, ratio_id: str,
                           fy: int) -> tuple[int | None, float | None, float | None, int | None]:
    """Fetch sector rank from peer_comparison for a financial_ratios metric.

    Returns (sector_rank, sector_percentile, sector_avg, peer_count).
    """
    try:
        row = con.execute(
            """SELECT sector_rank, sector_percentile, sector_avg, peer_count
               FROM peer_comparison
               WHERE ticker = ? AND metric_id = ? AND fiscal_year = ?
                 AND fiscal_period = 'FY' AND metric_source = 'financial_ratios'""",
            [ticker, ratio_id, fy],
        ).fetchone()
        if row:
            return row[0], row[1], row[2], row[3]
    except Exception:
        pass
    return None, None, None, None


def _fetch_net_margin(con, ticker: str, fy: int, fp: str) -> float | None:
    """Fetch net margin ratio value for pre-profitability check."""
    try:
        row = con.execute(
            """SELECT ratio_value FROM financial_ratios
               WHERE ticker = ? AND ratio_id = 'RATIO-003'
                 AND fiscal_year = ? AND fiscal_period = ?""",
            [ticker, fy, fp],
        ).fetchone()
        if row:
            return row[0]
    except Exception:
        pass
    return None


def _fetch_ratio_yoy(con, ticker: str, ratio_id: str, ratio_value: float,
                     fy: int) -> tuple[float | None, float | None]:
    """Compute YoY change for a ratio by comparing to previous year.

    Returns (yoy_change, yoy_pct).
    """
    try:
        row = con.execute(
            """SELECT ratio_value FROM financial_ratios
               WHERE ticker = ? AND ratio_id = ? AND fiscal_year = ?
                 AND fiscal_period = 'FY'""",
            [ticker, ratio_id, fy - 1],
        ).fetchone()
        if row:
            prev_val = row[0]
            yoy_change = ratio_value - prev_val
            yoy_pct = yoy_change / abs(prev_val) if prev_val != 0 else None
            return yoy_change, yoy_pct
    except Exception:
        pass
    return None, None


def _get_sector_stats(con, source: str, metric_id: str, sector: str,
                      fiscal_year: int) -> dict | None:
    """Compute sector statistics (avg, median, leader, laggard) for a metric.

    Returns dict with avg, median, leader, laggard, companies_reporting.
    Returns None if no data.
    """
    if source == "financial_ratios":
        val_rows = con.execute(
            """SELECT ticker, ratio_value FROM financial_ratios
               WHERE sector = ? AND ratio_id = ? AND fiscal_year = ?
                 AND fiscal_period = 'FY' ORDER BY ratio_value DESC""",
            [sector, metric_id, fiscal_year],
        ).fetchall()
        fmt_fn = _format_ratio_value
    else:
        val_rows = con.execute(
            """SELECT ticker, val FROM company_financials
               WHERE sector = ? AND business_term_id = ? AND fiscal_year = ?
                 AND fiscal_period = 'FY' ORDER BY val DESC""",
            [sector, metric_id, fiscal_year],
        ).fetchall()
        fmt_fn = _format_metric_value

    if not val_rows:
        return None

    values = [(t, v) for t, v in val_rows]
    all_vals = [v for _, v in values]
    avg = sum(all_vals) / len(all_vals)
    sorted_vals = sorted(all_vals)
    median = sorted_vals[len(sorted_vals) // 2]
    leader_tick, leader_val = values[0]
    laggard_tick, laggard_val = values[-1]

    return {
        "avg": avg,
        "avg_formatted": fmt_fn(avg, metric_id),
        "median": median,
        "median_formatted": fmt_fn(median, metric_id),
        "leader": {"ticker": leader_tick, "value": leader_val,
                   "formatted": fmt_fn(leader_val, metric_id)},
        "laggard": {"ticker": laggard_tick, "value": laggard_val,
                    "formatted": fmt_fn(laggard_val, metric_id)},
        "companies_reporting": len(values),
    }


# ---------------------------------------------------------------------------
# Tool 1: get_company_metric
# ---------------------------------------------------------------------------


def get_company_metric(
    ticker: str,
    metric: str,
    fiscal_year: int | None = None,
    fiscal_period: str = "FY",
) -> dict:
    """Get a specific metric for a company.

    Args:
        ticker: Company ticker (AAPL, MSFT, etc.)
        metric: Business term name or ID (e.g., "Revenue", "BT-022")
        fiscal_year: Specific year. If None, returns latest available.
        fiscal_period: FY, Q1, Q2, Q3. Default: FY.

    Returns:
        Dict with value, formatted, unit, yoy_change, yoy_pct, cagr_5yr,
        sector_rank, sector_percentile, peer_count, anomaly_flags, fiscal_year,
        period_end_date.
    """
    con = get_db()
    ticker = ticker.upper()

    try:
        bt_id, bt_name = _resolve_metric(metric)
    except ValueError as e:
        return {"error": str(e)}

    if fiscal_year is not None:
        rows = con.execute(
            """SELECT val, unit, fiscal_year, period_end_date, sector,
                      fiscal_year_end, canonical_name, cik
               FROM company_financials
               WHERE ticker = ? AND business_term_id = ?
                 AND fiscal_year = ? AND fiscal_period = ?""",
            [ticker, bt_id, fiscal_year, fiscal_period],
        ).fetchall()
    else:
        rows = con.execute(
            """SELECT val, unit, fiscal_year, period_end_date, sector,
                      fiscal_year_end, canonical_name, cik
               FROM company_financials
               WHERE ticker = ? AND business_term_id = ?
                 AND fiscal_period = ?
               ORDER BY fiscal_year DESC LIMIT 1""",
            [ticker, bt_id, fiscal_period],
        ).fetchall()

    if not rows:
        return {
            "error": f"{ticker} does not report {bt_name} for the requested period.",
            "ticker": ticker,
            "metric": bt_name,
            "fiscal_year": fiscal_year,
        }

    val, unit, fy, period_end_date, sector, fy_end, company_name, cik = rows[0]

    yoy_change, yoy_pct, cagr_5yr = _fetch_metric_growth(con, ticker, bt_id, fy, fiscal_period)
    sector_rank, sector_percentile, peer_count = _fetch_metric_peer_rank(con, ticker, bt_id, fy, fiscal_period)
    net_margin = _fetch_net_margin(con, ticker, fy, fiscal_period)

    anomaly_flags = check_anomalies(
        ticker=ticker, metric=bt_name, value=val,
        yoy_pct=yoy_pct, sector=sector, net_margin=net_margin,
    )

    result = {
        "ticker": ticker,
        "company_name": company_name,
        "metric": bt_name,
        "metric_id": bt_id,
        "value": val,
        "formatted": _format_metric_value(val, bt_id),
        "unit": unit,
        "fiscal_year": fy,
        "fiscal_period": fiscal_period,
        "period_end_date": str(period_end_date) if period_end_date else None,
        "fiscal_year_end": fy_end,
        "sector": sector,
    }

    if yoy_change is not None:
        result["yoy_change"] = yoy_change
        result["yoy_change_formatted"] = format_currency(yoy_change)
    if yoy_pct is not None:
        result["yoy_pct"] = yoy_pct
        result["yoy_pct_formatted"] = format_yoy_pct(yoy_pct)
    if cagr_5yr is not None:
        result["cagr_5yr"] = cagr_5yr
        result["cagr_5yr_formatted"] = format_yoy_pct(cagr_5yr)
    if sector_rank is not None:
        result["sector_rank"] = sector_rank
        result["sector_percentile"] = sector_percentile
        result["peer_count"] = peer_count
    if anomaly_flags:
        result["anomaly_flags"] = anomaly_flags

    return result


# ---------------------------------------------------------------------------
# Tool 2: get_company_profile
# ---------------------------------------------------------------------------


def get_company_profile(
    ticker: str,
    fiscal_year: int | None = None,
) -> dict:
    """Get a full financial profile for a company.

    Returns all metrics, ratios, and amendment summary for a given fiscal year.

    Args:
        ticker: Company ticker.
        fiscal_year: Default: latest available.

    Returns:
        Dict with company_info, metrics[], ratios[], amendment_summary, anomaly_flags.
    """
    con = get_db()
    ticker = ticker.upper()

    if fiscal_year is None:
        fy_rows = con.execute(
            """SELECT MAX(fiscal_year) FROM company_financials
               WHERE ticker = ? AND fiscal_period = 'FY'""",
            [ticker],
        ).fetchone()
        if fy_rows and fy_rows[0]:
            fiscal_year = fy_rows[0]
        else:
            return {"error": f"No data found for ticker {ticker}"}

    info_rows = con.execute(
        """SELECT DISTINCT canonical_name, sector, fiscal_year_end, cik
           FROM company_financials
           WHERE ticker = ? AND fiscal_year = ? AND fiscal_period = 'FY'
           LIMIT 1""",
        [ticker, fiscal_year],
    ).fetchall()

    if not info_rows:
        return {"error": f"No data found for {ticker} in FY{fiscal_year}"}

    company_name, sector, fy_end, cik = info_rows[0]

    company_info = {
        "ticker": ticker,
        "name": company_name,
        "sector": sector,
        "fiscal_year": fiscal_year,
        "fiscal_year_end": fy_end,
    }

    # Get all metrics
    metric_rows = con.execute(
        """SELECT business_term_id, business_term, val, unit
           FROM company_financials
           WHERE ticker = ? AND fiscal_year = ? AND fiscal_period = 'FY'
           ORDER BY business_term""",
        [ticker, fiscal_year],
    ).fetchall()

    metrics = []
    for bt_id, bt_name, val, unit in metric_rows:
        _, yoy_pct, _ = _fetch_metric_growth(con, ticker, bt_id, fiscal_year, "FY")
        sector_rank, _, peer_count = _fetch_metric_peer_rank(con, ticker, bt_id, fiscal_year, "FY")

        metrics.append({
            "name": bt_name,
            "metric_id": bt_id,
            "value": val,
            "formatted": _format_metric_value(val, bt_id),
            "yoy_pct": format_yoy_pct(yoy_pct) if yoy_pct is not None else None,
            "sector_rank": f"#{sector_rank} of {peer_count}" if sector_rank is not None else None,
        })

    # Get all ratios
    ratio_rows = con.execute(
        """SELECT ratio_id, ratio_name, ratio_value
           FROM financial_ratios
           WHERE ticker = ? AND fiscal_year = ? AND fiscal_period = 'FY'
           ORDER BY ratio_name""",
        [ticker, fiscal_year],
    ).fetchall()

    ratios = []
    for ratio_id, ratio_name, ratio_value in ratio_rows:
        r_rank, _, _, r_peer_count = _fetch_ratio_peer_rank(con, ticker, ratio_id, fiscal_year)

        ratios.append({
            "name": ratio_name,
            "ratio_id": ratio_id,
            "value": ratio_value,
            "formatted": _format_ratio_value(ratio_value, ratio_id),
            "sector_rank": f"#{r_rank} of {r_peer_count}" if r_rank is not None else None,
        })

    # Get amendment summary
    amendment_summary = None
    try:
        amend_rows = con.execute(
            """SELECT amendment_count, mean_abs_change, median_abs_change,
                      max_abs_change, mean_pct_change, days_to_amend_avg
               FROM amendment_analysis
               WHERE ticker = ? AND fiscal_year = ?""",
            [ticker, fiscal_year],
        ).fetchall()
        if amend_rows:
            a = amend_rows[0]
            amendment_summary = {
                "count": a[0],
                "avg_magnitude": format_currency(a[1]),
                "median_magnitude": format_currency(a[2]),
                "max_magnitude": format_currency(a[3]),
                "avg_pct_change": format_percentage(a[4]) if a[4] is not None else None,
                "avg_days_to_amend": round(a[5], 1) if a[5] else None,
            }
    except Exception:
        pass

    # Collect anomaly flags for key metrics
    anomaly_flags = []

    net_margin = None
    for r in ratios:
        if r["ratio_id"] == "RATIO-003":
            net_margin = r["value"]
            break

    for m in metrics:
        flags = check_anomalies(
            ticker=ticker, metric=m["name"], value=m["value"],
            sector=sector, net_margin=net_margin,
        )
        for f in flags:
            if f not in anomaly_flags:
                anomaly_flags.append(f)

    for r in ratios:
        flags = check_anomalies(
            ticker=ticker, metric=r["name"], value=r["value"],
            sector=sector, ratio_name=r["name"],
        )
        for f in flags:
            if f not in anomaly_flags:
                anomaly_flags.append(f)

    result = {
        "company_info": company_info,
        "metrics": metrics,
        "ratios": ratios,
    }

    if amendment_summary:
        result["amendment_summary"] = amendment_summary
    if anomaly_flags:
        result["anomaly_flags"] = anomaly_flags

    return result


# ---------------------------------------------------------------------------
# Tool 3: compare_companies
# ---------------------------------------------------------------------------


def compare_companies(
    ticker_a: str,
    ticker_b: str,
    fiscal_year: int | None = None,
    metrics: list[str] | None = None,
) -> dict:
    """Compare two companies on financial metrics.

    Args:
        ticker_a: First company ticker.
        ticker_b: Second company ticker.
        fiscal_year: Default: latest year where both have data.
        metrics: Specific metrics to compare. Default: all shared metrics.

    Returns:
        Dict with company_a, company_b, comparisons[], fiscal_alignment_warning.
    """
    con = get_db()
    ticker_a = ticker_a.upper()
    ticker_b = ticker_b.upper()

    if fiscal_year is None:
        fy_rows = con.execute(
            """SELECT MAX(fiscal_year) FROM (
                 SELECT fiscal_year FROM company_financials
                 WHERE ticker = ? AND fiscal_period = 'FY'
                 INTERSECT
                 SELECT fiscal_year FROM company_financials
                 WHERE ticker = ? AND fiscal_period = 'FY'
               )""",
            [ticker_a, ticker_b],
        ).fetchone()
        if fy_rows and fy_rows[0]:
            fiscal_year = fy_rows[0]
        else:
            return {"error": f"No overlapping fiscal years for {ticker_a} and {ticker_b}"}

    def _get_company_info(ticker: str) -> dict:
        row = con.execute(
            """SELECT DISTINCT canonical_name, sector, fiscal_year_end, cik
               FROM company_financials
               WHERE ticker = ? AND fiscal_year = ? AND fiscal_period = 'FY'
               LIMIT 1""",
            [ticker, fiscal_year],
        ).fetchone()
        if row:
            return {"ticker": ticker, "name": row[0], "sector": row[1], "fiscal_year_end": row[2]}
        return {"ticker": ticker}

    company_a = _get_company_info(ticker_a)
    company_b = _get_company_info(ticker_b)

    if metrics:
        resolved_metrics = []
        for m in metrics:
            try:
                source, mid, mname = _detect_metric_or_ratio(m)
                resolved_metrics.append((source, mid, mname))
            except ValueError:
                continue
    else:
        shared = con.execute(
            """SELECT a.business_term_id, a.business_term
               FROM company_financials a
               JOIN company_financials b
                 ON a.business_term_id = b.business_term_id
                AND a.fiscal_year = b.fiscal_year
                AND a.fiscal_period = b.fiscal_period
               WHERE a.ticker = ? AND b.ticker = ?
                 AND a.fiscal_year = ? AND a.fiscal_period = 'FY'""",
            [ticker_a, ticker_b, fiscal_year],
        ).fetchall()
        resolved_metrics = [("company_financials", bt_id, bt_name) for bt_id, bt_name in shared]

        shared_ratios = con.execute(
            """SELECT a.ratio_id, a.ratio_name
               FROM financial_ratios a
               JOIN financial_ratios b
                 ON a.ratio_id = b.ratio_id
                AND a.fiscal_year = b.fiscal_year
                AND a.fiscal_period = b.fiscal_period
               WHERE a.ticker = ? AND b.ticker = ?
                 AND a.fiscal_year = ? AND a.fiscal_period = 'FY'""",
            [ticker_a, ticker_b, fiscal_year],
        ).fetchall()
        resolved_metrics.extend(
            [("financial_ratios", rid, rname) for rid, rname in shared_ratios]
        )

    comparisons = []
    for source, mid, mname in resolved_metrics:
        if source == "company_financials":
            val_a_row = con.execute(
                """SELECT val FROM company_financials
                   WHERE ticker = ? AND business_term_id = ?
                     AND fiscal_year = ? AND fiscal_period = 'FY'""",
                [ticker_a, mid, fiscal_year],
            ).fetchone()
            val_b_row = con.execute(
                """SELECT val FROM company_financials
                   WHERE ticker = ? AND business_term_id = ?
                     AND fiscal_year = ? AND fiscal_period = 'FY'""",
                [ticker_b, mid, fiscal_year],
            ).fetchone()
            val_a = val_a_row[0] if val_a_row else None
            val_b = val_b_row[0] if val_b_row else None
            fmt_a = _format_metric_value(val_a, mid)
            fmt_b = _format_metric_value(val_b, mid)
        else:
            val_a_row = con.execute(
                """SELECT ratio_value FROM financial_ratios
                   WHERE ticker = ? AND ratio_id = ?
                     AND fiscal_year = ? AND fiscal_period = 'FY'""",
                [ticker_a, mid, fiscal_year],
            ).fetchone()
            val_b_row = con.execute(
                """SELECT ratio_value FROM financial_ratios
                   WHERE ticker = ? AND ratio_id = ?
                     AND fiscal_year = ? AND fiscal_period = 'FY'""",
                [ticker_b, mid, fiscal_year],
            ).fetchone()
            val_a = val_a_row[0] if val_a_row else None
            val_b = val_b_row[0] if val_b_row else None
            fmt_a = _format_ratio_value(val_a, mid)
            fmt_b = _format_ratio_value(val_b, mid)

        if val_a is None or val_b is None:
            continue

        delta = val_a - val_b
        delta_pct = delta / abs(val_b) if val_b != 0 else None
        winner = ticker_a if val_a > val_b else ticker_b if val_b > val_a else "tie"

        comparisons.append({
            "metric": mname,
            "metric_id": mid,
            "source": source,
            "value_a": val_a,
            "value_b": val_b,
            "formatted_a": fmt_a,
            "formatted_b": fmt_b,
            "delta": delta,
            "delta_pct": delta_pct,
            "delta_pct_formatted": format_yoy_pct(delta_pct) if delta_pct is not None else None,
            "winner": winner,
        })

    result = {
        "company_a": company_a,
        "company_b": company_b,
        "fiscal_year": fiscal_year,
        "comparisons": comparisons,
    }

    fy_warning = check_fiscal_alignment(
        ticker_a, company_a.get("fiscal_year_end"),
        ticker_b, company_b.get("fiscal_year_end"),
    )
    if fy_warning:
        result["fiscal_alignment_warning"] = fy_warning

    return result


# ---------------------------------------------------------------------------
# Tool 4: rank_companies
# ---------------------------------------------------------------------------


def rank_companies(
    metric: str,
    fiscal_year: int | None = None,
    sector: str | None = None,
    top_n: int | None = None,
    metric_source: str | None = None,
) -> dict:
    """Rank companies by a metric.

    Args:
        metric: Metric name or ID to rank by.
        fiscal_year: Default: latest.
        sector: Filter to sector. Default: all companies.
        top_n: How many to return. Default: all.
        metric_source: "company_financials" or "financial_ratios". Default: auto-detect.

    Returns:
        Dict with rankings[], metric_name, fiscal_year, companies_included.
    """
    con = get_db()

    if metric_source is None:
        try:
            source, mid, mname = _detect_metric_or_ratio(metric)
            metric_source = source
        except ValueError as e:
            return {"error": str(e)}
    else:
        if metric_source == "financial_ratios":
            mid, mname = _resolve_ratio(metric)
        else:
            mid, mname = _resolve_metric(metric)
        source = metric_source

    if fiscal_year is None:
        if metric_source == "financial_ratios":
            fy_row = con.execute(
                "SELECT MAX(fiscal_year) FROM financial_ratios WHERE ratio_id = ? AND fiscal_period = 'FY'",
                [mid],
            ).fetchone()
        else:
            fy_row = con.execute(
                "SELECT MAX(fiscal_year) FROM company_financials WHERE business_term_id = ? AND fiscal_period = 'FY'",
                [mid],
            ).fetchone()
        if fy_row and fy_row[0]:
            fiscal_year = fy_row[0]
        else:
            return {"error": f"No data found for metric {mname}"}

    if metric_source == "financial_ratios":
        query = """SELECT ticker, canonical_name, sector, ratio_value
                   FROM financial_ratios
                   WHERE ratio_id = ? AND fiscal_year = ? AND fiscal_period = 'FY'"""
    else:
        query = """SELECT ticker, canonical_name, sector, val
                   FROM company_financials
                   WHERE business_term_id = ? AND fiscal_year = ? AND fiscal_period = 'FY'"""
    params = [mid, fiscal_year]
    if sector:
        query += " AND sector = ?"
        params.append(sector)
    query += " ORDER BY " + ("ratio_value" if metric_source == "financial_ratios" else "val") + " DESC"
    rows = con.execute(query, params).fetchall()
    values = [(r[0], r[1], r[2], r[3]) for r in rows]

    fmt_fn = _format_ratio_value if metric_source == "financial_ratios" else _format_metric_value
    rankings = []
    for rank, (tick, name, sec, val) in enumerate(values, start=1):
        rankings.append({
            "rank": rank, "ticker": tick, "name": name, "sector": sec,
            "value": val, "formatted": fmt_fn(val, mid),
        })

    if top_n is not None:
        rankings = rankings[:top_n]

    return {
        "metric_name": mname, "metric_id": mid,
        "fiscal_year": fiscal_year, "companies_included": len(values),
        "sector_filter": sector, "rankings": rankings,
    }


# ---------------------------------------------------------------------------
# Tool 5: get_company_trend
# ---------------------------------------------------------------------------


def get_company_trend(
    ticker: str,
    metric: str,
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict:
    """Get a metric trend over time for a company.

    Args:
        ticker: Company ticker.
        metric: Metric name or ID.
        start_year: Default: earliest available.
        end_year: Default: latest available.

    Returns:
        Dict with time_series[], cagr_5yr, trend_direction, anomaly_flags.
    """
    con = get_db()
    ticker = ticker.upper()

    try:
        bt_id, bt_name = _resolve_metric(metric)
    except ValueError as e:
        return {"error": str(e)}

    query = """SELECT fiscal_year, val, period_end_date, sector
               FROM company_financials
               WHERE ticker = ? AND business_term_id = ? AND fiscal_period = 'FY'"""
    params: list = [ticker, bt_id]
    if start_year is not None:
        query += " AND fiscal_year >= ?"
        params.append(start_year)
    if end_year is not None:
        query += " AND fiscal_year <= ?"
        params.append(end_year)
    query += " ORDER BY fiscal_year ASC"
    rows = con.execute(query, params).fetchall()

    if not rows:
        return {"error": f"No data found for {ticker} {bt_name}", "ticker": ticker, "metric": bt_name}

    # Batch-fetch YoY data for all years at once
    pop_query = """SELECT fiscal_year, growth_type, growth_value
                   FROM period_over_period
                   WHERE ticker = ? AND business_term_id = ? AND fiscal_period = 'FY'
                     AND growth_type IN ('yoy_change', 'yoy_pct_change')"""
    pop_params: list = [ticker, bt_id]
    if start_year:
        pop_query += " AND fiscal_year >= ?"
        pop_params.append(start_year)
    if end_year:
        pop_query += " AND fiscal_year <= ?"
        pop_params.append(end_year)

    pop_data: dict[tuple, float] = {}
    for fy, gtype, gval in con.execute(pop_query, pop_params).fetchall():
        pop_data[(fy, gtype)] = gval

    time_series = []
    all_yoy_pcts = []

    for fy, val, period_end, sector in rows:
        yoy_change = pop_data.get((fy, "yoy_change"))
        yoy_pct = pop_data.get((fy, "yoy_pct_change"))
        if yoy_pct is not None:
            all_yoy_pcts.append(yoy_pct)

        entry = {
            "fiscal_year": fy, "value": val,
            "formatted": _format_metric_value(val, bt_id),
            "period_end_date": str(period_end) if period_end else None,
        }
        if yoy_change is not None:
            entry["yoy_change"] = yoy_change
            entry["yoy_change_formatted"] = format_currency(yoy_change)
        if yoy_pct is not None:
            entry["yoy_pct"] = yoy_pct
            entry["yoy_pct_formatted"] = format_yoy_pct(yoy_pct)
        time_series.append(entry)

    # Get CAGR
    cagr_5yr = None
    latest_fy = rows[-1][0]
    try:
        cagr_row = con.execute(
            """SELECT growth_value FROM period_over_period
               WHERE ticker = ? AND business_term_id = ?
                 AND fiscal_year = ? AND fiscal_period = 'FY'
                 AND growth_type = 'cagr_5yr'""",
            [ticker, bt_id, latest_fy],
        ).fetchone()
        if cagr_row:
            cagr_5yr = cagr_row[0]
    except Exception:
        pass

    # Collect anomaly flags
    anomaly_flags = []
    for entry in time_series:
        flags = check_anomalies(
            ticker=ticker, metric=bt_name, value=entry["value"],
            yoy_pct=entry.get("yoy_pct"), sector=sector if rows else None,
        )
        for f in flags:
            if f not in anomaly_flags:
                anomaly_flags.append(f)

    result = {
        "ticker": ticker, "metric": bt_name, "metric_id": bt_id,
        "time_series": time_series, "trend_direction": _compute_trend_direction(all_yoy_pcts),
    }
    if cagr_5yr is not None:
        result["cagr_5yr"] = cagr_5yr
        result["cagr_5yr_formatted"] = format_yoy_pct(cagr_5yr)
    if anomaly_flags:
        result["anomaly_flags"] = anomaly_flags

    return result


# ---------------------------------------------------------------------------
# Tool 6: get_sector_summary
# ---------------------------------------------------------------------------


def get_sector_summary(
    sector: str,
    fiscal_year: int | None = None,
    metric: str | None = None,
) -> dict:
    """Get a summary of a sector's financial performance.

    Args:
        sector: Sector name (e.g., "Technology").
        fiscal_year: Default: latest.
        metric: Specific metric. Default: key metrics (Revenue, Net Income, Net Margin).

    Returns:
        Dict with sector, companies[], metric_summary[], fiscal_year.
    """
    con = get_db()

    if fiscal_year is None:
        fy_row = con.execute(
            "SELECT MAX(fiscal_year) FROM company_financials WHERE sector = ? AND fiscal_period = 'FY'",
            [sector],
        ).fetchone()
        if fy_row and fy_row[0]:
            fiscal_year = fy_row[0]
        else:
            return {"error": f"No data found for sector '{sector}'"}

    company_rows = con.execute(
        """SELECT DISTINCT ticker, canonical_name FROM company_financials
           WHERE sector = ? AND fiscal_year = ? AND fiscal_period = 'FY' ORDER BY ticker""",
        [sector, fiscal_year],
    ).fetchall()

    if not company_rows:
        return {"error": f"No companies found in sector '{sector}' for FY{fiscal_year}"}

    companies = [{"ticker": t, "name": n} for t, n in company_rows]

    if metric:
        try:
            source, mid, mname = _detect_metric_or_ratio(metric)
            metrics_to_query = [(source, mid, mname)]
        except ValueError as e:
            return {"error": str(e)}
    else:
        metrics_to_query = [
            ("company_financials", "BT-022", "Revenue"),
            ("company_financials", "BT-023", "Net Income"),
            ("financial_ratios", "RATIO-003", "Net Margin"),
        ]

    metric_summaries = []
    for source, mid, mname in metrics_to_query:
        stats = _get_sector_stats(con, source, mid, sector, fiscal_year)
        if stats is None:
            continue
        metric_summaries.append({"metric": mname, "metric_id": mid, "source": source, **stats})

    return {
        "sector": sector, "fiscal_year": fiscal_year,
        "companies": companies, "metric_summary": metric_summaries,
    }


# ---------------------------------------------------------------------------
# Tool 7: get_ratio
# ---------------------------------------------------------------------------


def get_ratio(
    ticker: str,
    ratio: str,
    fiscal_year: int | None = None,
) -> dict:
    """Get a financial ratio with component breakdown.

    Args:
        ticker: Company ticker.
        ratio: Ratio name or ID (e.g., "Net Margin", "RATIO-003").
        fiscal_year: Default: latest.

    Returns:
        Dict with ratio_name, value, formatted, numerator, denominator,
        sector_rank, sector_percentile, sector_avg, yoy_change, anomaly_flags.
    """
    con = get_db()
    ticker = ticker.upper()

    try:
        ratio_id, ratio_name = _resolve_ratio(ratio)
    except ValueError as e:
        return {"error": str(e)}

    if fiscal_year is not None:
        rows = con.execute(
            """SELECT ratio_value, numerator_bt_id, numerator_bt_name,
                      numerator_val, denominator_bt_id, denominator_bt_name,
                      denominator_val, fiscal_year, sector, fiscal_year_end
               FROM financial_ratios
               WHERE ticker = ? AND ratio_id = ? AND fiscal_year = ?
                 AND fiscal_period = 'FY'""",
            [ticker, ratio_id, fiscal_year],
        ).fetchall()
    else:
        rows = con.execute(
            """SELECT ratio_value, numerator_bt_id, numerator_bt_name,
                      numerator_val, denominator_bt_id, denominator_bt_name,
                      denominator_val, fiscal_year, sector, fiscal_year_end
               FROM financial_ratios
               WHERE ticker = ? AND ratio_id = ? AND fiscal_period = 'FY'
               ORDER BY fiscal_year DESC LIMIT 1""",
            [ticker, ratio_id],
        ).fetchall()

    if not rows:
        return {
            "error": f"{ticker} does not have {ratio_name} for the requested period.",
            "ticker": ticker, "ratio": ratio_name,
        }

    (ratio_value, num_bt_id, num_bt_name, num_val, den_bt_id, den_bt_name,
     den_val, fy, sector, fy_end) = rows[0]

    sector_rank, sector_percentile, sector_avg, peer_count = _fetch_ratio_peer_rank(con, ticker, ratio_id, fy)
    yoy_change, yoy_pct = _fetch_ratio_yoy(con, ticker, ratio_id, ratio_value, fy)

    anomaly_flags = check_anomalies(
        ticker=ticker, metric=ratio_name, value=ratio_value,
        yoy_pct=yoy_pct, sector=sector, ratio_name=ratio_name,
    )

    result = {
        "ticker": ticker,
        "ratio_name": ratio_name,
        "ratio_id": ratio_id,
        "value": ratio_value,
        "formatted": _format_ratio_value(ratio_value, ratio_id),
        "fiscal_year": fy,
        "numerator": {
            "bt_name": num_bt_name, "bt_id": num_bt_id,
            "value": num_val, "formatted": _format_metric_value(num_val, num_bt_id),
        },
        "denominator": {
            "bt_name": den_bt_name, "bt_id": den_bt_id,
            "value": den_val, "formatted": _format_metric_value(den_val, den_bt_id),
        },
    }

    if sector_rank is not None:
        result["sector_rank"] = sector_rank
        result["sector_percentile"] = sector_percentile
        result["sector_avg"] = sector_avg
        result["sector_avg_formatted"] = _format_ratio_value(sector_avg, ratio_id)
        result["peer_count"] = peer_count
    if yoy_change is not None:
        result["yoy_change"] = yoy_change
    if yoy_pct is not None:
        result["yoy_pct"] = yoy_pct
        result["yoy_pct_formatted"] = format_yoy_pct(yoy_pct)
    if anomaly_flags:
        result["anomaly_flags"] = anomaly_flags

    return result


# ---------------------------------------------------------------------------
# Tool 8: get_amendment_summary
# ---------------------------------------------------------------------------


def get_amendment_summary(
    ticker: str,
    fiscal_year: int | None = None,
) -> dict:
    """Get amendment analysis summary for a company.

    Args:
        ticker: Company ticker (AAPL, MSFT, etc.)
        fiscal_year: Specific year. If None, returns the latest available year.

    Returns:
        Dict with ticker, company_name, fiscal_year, amendment_count,
        distinct_concepts, mean/median/max abs change (formatted),
        largest_concept, days_to_amend_avg, total_val_impact (formatted).
    """
    con = get_db()
    ticker = ticker.upper()

    if fiscal_year is not None:
        rows = con.execute(
            """SELECT ticker, canonical_name, fiscal_year, amendment_count,
                      distinct_concepts, mean_abs_change, median_abs_change,
                      max_abs_change, largest_concept, days_to_amend_avg,
                      total_val_impact
               FROM amendment_analysis
               WHERE ticker = ? AND fiscal_year = ?""",
            [ticker, fiscal_year],
        ).fetchall()
    else:
        rows = con.execute(
            """SELECT ticker, canonical_name, fiscal_year, amendment_count,
                      distinct_concepts, mean_abs_change, median_abs_change,
                      max_abs_change, largest_concept, days_to_amend_avg,
                      total_val_impact
               FROM amendment_analysis
               WHERE ticker = ?
               ORDER BY fiscal_year DESC LIMIT 1""",
            [ticker],
        ).fetchall()

    if not rows:
        return {
            "error": f"No amendment data found for {ticker}"
            + (f" in FY{fiscal_year}" if fiscal_year else ""),
            "ticker": ticker,
        }

    (tick, company_name, fy, amendment_count, distinct_concepts,
     mean_abs, median_abs, max_abs, largest_concept,
     days_to_amend_avg, total_val_impact) = rows[0]

    return {
        "ticker": tick,
        "company_name": company_name,
        "fiscal_year": fy,
        "amendment_count": amendment_count,
        "distinct_concepts": distinct_concepts,
        "mean_abs_change": format_currency(mean_abs),
        "median_abs_change": format_currency(median_abs),
        "max_abs_change": format_currency(max_abs),
        "largest_concept": largest_concept,
        "days_to_amend_avg": round(days_to_amend_avg, 1),
        "total_val_impact": format_currency(total_val_impact),
    }
