# AI-Ready Zone: Deduplicate Tool Enrichment Logic

## Status: 🟢 COMPLETE

| Status | Meaning |
|--------|---------|
| 🟡 DRAFT | Riffing / initial design |
| 🔵 ARCH REVIEW | Awaiting @governance-reviewer approval |
| 🟠 IMPLEMENTATION | Agent pipeline running |
| 🟣 TESTING | DQ rules and validation |
| 🔴 CODE REVIEW | Reviewing |
| ✅ VERIFICATION | Build + DQ + governance verification |
| 🟢 COMPLETE | Shipped |
| ⚫ BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-03-15 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-03-15 |
| Zone | AI-Ready |
| Primary Agent | @primary-agent |
| Blocked By | — |
| Depends On | `ai-ready-chat-interface` (🟢 COMPLETE) |

---

## Claude Code Prompt

```
make a spec and do it
```

---

## 1. Feature Description

### Problem Statement

`src/ai_ready/tools/financial_tools.py` is 1,390 lines with significant copy-paste duplication. Every tool function that returns a metric independently fetches YoY growth, sector rank, net margin, and anomaly flags using nearly identical SQL + Python blocks:

| Pattern | Instances | ~Lines each |
|---------|-----------|-------------|
| Fetch YoY from period_over_period | 4 | 15 |
| Fetch sector rank from peer_comparison | 4 | 12 |
| Fetch net margin for anomaly check | 3 | 10 |
| check_anomalies() call | 4 | 8 |

~250-300 lines of duplicated enrichment logic.

### User Story

As a developer maintaining the AI-Ready tools, I want enrichment logic (growth, peer rank, anomalies) extracted into shared helpers so that bug fixes and new enrichment features apply to all tools without copy-paste.

### Success Criteria

1. Extract `_enrich_metric()` and `_enrich_ratio()` helpers
2. All 7 tool functions use the shared helpers instead of inline SQL
3. All existing tests pass with identical output
4. 88/88 verification checks still pass
5. File reduced from ~1,390 lines to ~900 or fewer
6. Zero behavioral changes — pure refactor

---

## 2. Design

### `_enrich_metric(con, ticker, bt_id, fy, fp, sector)` → dict

Returns:
```python
{
    "yoy_change": float | None,
    "yoy_pct": float | None,
    "cagr_5yr": float | None,
    "sector_rank": int | None,
    "sector_percentile": float | None,
    "peer_count": int | None,
    "net_margin": float | None,
    "anomaly_flags": list[str],
}
```

### `_enrich_ratio(con, ticker, ratio_id, ratio_name, fy, fp, sector, value)` → dict

Returns:
```python
{
    "sector_rank": int | None,
    "sector_percentile": float | None,
    "peer_count": int | None,
    "anomaly_flags": list[str],
}
```

### Consumers

| Tool | Currently duplicates | After |
|------|---------------------|-------|
| `get_company_metric` | YoY + rank + anomalies | `_enrich_metric()` |
| `get_company_profile` | YoY + rank per metric, rank per ratio | `_enrich_metric()` per metric, `_enrich_ratio()` per ratio |
| `get_company_trend` | anomalies per year | `_enrich_metric()` per year |
| `get_ratio` | rank + anomalies | `_enrich_ratio()` |
| `compare_companies` | No enrichment duplication | No change |
| `rank_companies` | No enrichment duplication | No change |
| `get_sector_summary` | Minimal anomaly check | `_enrich_metric()` loop |
| `get_amendment_summary` | No enrichment | No change |

---

## 3. Rollout

1. Extract helpers into the same file (no new files)
2. Refactor each tool function one at a time
3. Run tests after each function change
4. Run 88/88 verification at the end

---

## 4. Risk

| Risk | Mitigation |
|------|-----------|
| Subtle behavioral difference in enrichment | Tests + 88/88 verification |
| Performance regression from extra queries | No change — same queries, just centralized |
