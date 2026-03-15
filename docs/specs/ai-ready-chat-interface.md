# AI-Ready Zone: Chat Interface

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
| Depends On | All 5 consumable specs (🟢 COMPLETE) |
| Informed By | `governance/insights/consumable-to-ai-ready-insights.md`, genai-architect review |

---

## Claude Code Prompt

```
Implement the ai-ready-chat-interface spec.

This is the AI-Ready zone — the final layer. Instead of creating new Iceberg tables,
this builds a tool-use chat interface that lets users ask natural language questions
about the financial data. Claude queries the 5 consumable Iceberg tables via 7
validated Python tool functions. No embeddings, no RAG, no pre-computed documents.

Follow the spec exactly. The architecture decision is: tool use over DuckDB, not RAG.
```

---

## 1. Feature Description

### Problem Statement

The consumable zone has 125,814 rows across 5 clean tables covering 20 companies, 25 financial metrics, 7 ratios, growth trends, peer rankings, and amendment patterns. But answering "Is Boeing's financial health deteriorating?" requires querying 5 tables, joining results, interpreting anomalies, and formatting numbers — all before generating a response. A financial analyst could do this in SQL; an LLM cannot do it reliably without validated query tools.

### Architecture Decision

**Tool use over DuckDB. No RAG. No embeddings. No pre-computed documents.**

| Approach | Verdict | Why |
|----------|---------|-----|
| **Tool use (chosen)** | Build this | Claude calls 7 validated Python functions that run parameterized DuckDB queries. Claude never writes SQL. Results include formatted values, anomaly flags, and fiscal alignment warnings. |
| Text-to-SQL | Rejected | Fragile. Claude halluccinates column names, misuses the long-format schema, and produces fiscal year join bugs. |
| RAG + embeddings | Rejected | Wrong architecture. RAG solves "find the relevant passage in a large unstructured corpus." We have 5 structured tables and DuckDB. Embeddings add infrastructure, staleness, and a failure mode for zero benefit. |
| Pre-computed documents | Rejected | DuckDB joins 5 tables in milliseconds. Pre-computing 340 company profiles that go stale when data changes is premature optimization. |

### User Story

As a user, I want to type "Compare Apple and Microsoft's profitability over the last 5 years" and get an accurate, well-formatted answer that cites specific numbers from the real Iceberg data — not hallucinated values, not stale pre-computed text.

### Success Criteria

- [ ] 7 tool functions that query real Iceberg data
- [ ] Claude agent loop with tool use (Anthropic SDK)
- [ ] System prompt with schema context, anomaly flags, metric definitions, company roster
- [ ] Number formatting ($394.3B, 25.3%, rank #1 of 5)
- [ ] Anomaly flags attached to unusual data points
- [ ] Fiscal year alignment warnings on cross-company comparisons
- [ ] CLI entry point: `python -m src.ai_ready.cli`
- [ ] Interactive chat session with conversation history
- [ ] All tool functions tested against real Iceberg data
- [ ] Graceful handling of missing data ("Boeing does not report Gross Profit")

## 2. Technical Design

### 2.1 Architecture

```
User Question
    │
    ▼
┌──────────────────────────────────┐
│  Claude (tool_use)               │
│  System prompt:                  │
│  - 20 companies + metadata       │
│  - 25 metrics + 7 ratios         │
│  - Known anomalies (~20 flags)   │
│  - Fiscal year alignment rules   │
│  - Tool schemas                  │
└──────────┬───────────────────────┘
           │ tool calls
           ▼
┌──────────────────────────────────┐
│  7 Tool Functions                │
│  (validated, parameterized)      │
│                                  │
│  get_company_metric()            │
│  get_company_profile()           │
│  compare_companies()             │
│  rank_companies()                │
│  get_company_trend()             │
│  get_sector_summary()            │
│  get_ratio()                     │
└──────────┬───────────────────────┘
           │ DuckDB SQL
           ▼
┌──────────────────────────────────┐
│  5 Consumable Iceberg Tables     │
│  (125,814 rows, read-only)       │
└──────────────────────────────────┘
```

### 2.2 The 7 Tools

#### Tool 1: `get_company_metric`
**When Claude uses it:** "What was Apple's revenue in 2024?"

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ticker | str | Yes | Company ticker (AAPL, MSFT, etc.) |
| metric | str | Yes | Business term name or ID (e.g., "Revenue", "BT-022") |
| fiscal_year | int | No | Specific year. If omitted, returns latest. |
| fiscal_period | str | No | FY, Q1, Q2, Q3. Default: FY |

**Returns:** `{ value, formatted, unit, yoy_change, yoy_pct, cagr_5yr, sector_rank, sector_percentile, peer_count, anomaly_flags[], fiscal_year, period_end_date }`

**Queries:** company_financials + period_over_period + peer_comparison

#### Tool 2: `get_company_profile`
**When Claude uses it:** "Tell me about Apple's FY2024 financials"

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ticker | str | Yes | Company ticker |
| fiscal_year | int | No | Default: latest available |

**Returns:** `{ company_info{}, metrics[]{name, value, formatted, yoy_pct, sector_rank}, ratios[]{name, value, formatted, sector_rank}, amendment_summary{count, avg_magnitude}, anomaly_flags[] }`

**Queries:** All 5 tables joined on (cik, fiscal_year)

#### Tool 3: `compare_companies`
**When Claude uses it:** "Compare Apple and Microsoft on profitability"

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ticker_a | str | Yes | First company |
| ticker_b | str | Yes | Second company |
| fiscal_year | int | No | Default: latest |
| metrics | list[str] | No | Specific metrics. Default: all shared metrics. |

**Returns:** `{ company_a{}, company_b{}, comparisons[]{metric, value_a, value_b, formatted_a, formatted_b, delta, delta_pct, winner}, fiscal_alignment_warning (if FY ends differ) }`

**Queries:** company_financials + financial_ratios for both companies

#### Tool 4: `rank_companies`
**When Claude uses it:** "Which company has the highest net margin?"

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| metric | str | Yes | Metric to rank by |
| fiscal_year | int | No | Default: latest |
| sector | str | No | Filter to sector. Default: all companies. |
| top_n | int | No | How many to return. Default: all. |
| metric_source | str | No | `company_financials` or `financial_ratios`. Default: auto-detect. |

**Returns:** `{ rankings[]{rank, ticker, name, sector, value, formatted}, metric_name, fiscal_year, companies_included }`

**Queries:** company_financials or financial_ratios + peer_comparison

#### Tool 5: `get_company_trend`
**When Claude uses it:** "How has Apple's revenue changed over time?"

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ticker | str | Yes | Company ticker |
| metric | str | Yes | Metric to track |
| start_year | int | No | Default: earliest available |
| end_year | int | No | Default: latest available |

**Returns:** `{ time_series[]{fiscal_year, value, formatted, yoy_change, yoy_pct}, cagr_5yr (if available), trend_direction ("growing"/"declining"/"volatile"/"stable"), anomaly_flags[] }`

**Queries:** company_financials + period_over_period

#### Tool 6: `get_sector_summary`
**When Claude uses it:** "How is the Technology sector performing?"

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sector | str | Yes | Sector name |
| fiscal_year | int | No | Default: latest |
| metric | str | No | Specific metric. Default: key metrics (Revenue, Net Income, Net Margin). |

**Returns:** `{ sector, companies[]{ticker, name}, metric_summary[]{metric, avg, median, leader{ticker, value}, laggard{ticker, value}}, fiscal_year }`

**Queries:** peer_comparison + company_financials

#### Tool 7: `get_ratio`
**When Claude uses it:** "What is Apple's debt-to-equity ratio?"

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ticker | str | Yes | Company ticker |
| ratio | str | Yes | Ratio name or ID (e.g., "Net Margin", "RATIO-003") |
| fiscal_year | int | No | Default: latest |

**Returns:** `{ ratio_name, value, formatted, numerator{bt_name, value, formatted}, denominator{bt_name, value, formatted}, sector_rank, sector_percentile, sector_avg, yoy_change, anomaly_flags[] }`

**Queries:** financial_ratios + peer_comparison + period_over_period

### 2.3 Number Formatting

All tool responses include both raw values and formatted strings:

| Value Range | Format | Example |
|-------------|--------|---------|
| >= 1 trillion | $X.XT | $1.2T |
| >= 1 billion | $X.XB | $394.3B |
| >= 1 million | $X.XM | $97.0M |
| >= 1 thousand | $X.XK | $6.5K |
| < 1 thousand | $X.XX | $3.50 |
| Ratios/margins | X.X% | 25.3% |
| Per-share | $X.XX | $6.42 |
| Negative | ($X.XB) | ($1.2B) |

### 2.4 Anomaly Flags

Tool responses include anomaly flags when data points need caveats. Flags are computed at query time from known rules, not stored in Iceberg:

| Rule | Trigger | Flag Text |
|------|---------|-----------|
| Extreme YoY | \|yoy_pct\| > 2.0 (200%) | "Unusually large year-over-year change ({pct}%). May reflect M&A, reclassification, or one-time event." |
| Negative equity | ticker=BA AND metric=Stockholders Equity AND val < 0 | "Negative stockholders equity. Debt-to-equity ratio reflects negative equity denominator, not extreme debt." |
| Extreme D/E | D/E > 50 | "Extreme leverage ratio ({value}x) driven by near-zero or negative equity denominator." |
| Negative revenue | val < 0 AND metric=Revenue | "Data quality anomaly in source XBRL filing. Exercise caution." |
| Pre-profit company | Net Margin < -1.0 | "Pre-profitability period. Operating losses exceeded revenue." |
| Financial sector missing ratios | sector=Financials AND metric in (Gross Margin, Operating Margin) | "Financial institutions use different P&L structures. This metric is not applicable." |
| Fiscal year misalignment | Comparison where FY ends differ by > 30 days | "Fiscal year ends differ: {ticker_a} ({fy_end_a}) vs {ticker_b} ({fy_end_b}). Comparison covers different calendar periods." |

### 2.5 System Prompt

The system prompt (~3,000 tokens) includes:

1. **Company roster** — 20 companies with ticker, name, sector, fiscal year end
2. **Metric catalog** — 25 business terms + 7 ratios with brief definitions
3. **Known anomalies** — Static list of ~15-20 known data quality issues
4. **Interpretation guide** — "Higher Net Margin = more profitable", "Debt-to-Equity > 1 = more debt than equity"
5. **Fiscal year alignment rules** — Which companies have non-December FY ends
6. **Scope declaration** — "This dataset covers 20 large-cap US companies from FY2009-2026. Sector averages are based on 2-5 companies, not representative of full sectors."
7. **Formatting instructions** — Always cite specific numbers, always note fiscal year, flag anomalies

### 2.6 Module Structure

```
src/ai_ready/
    __init__.py
    tools/
        __init__.py
        financial_tools.py     # 7 tool functions
        anomaly_checker.py     # Anomaly flag rules
        formatters.py          # Number formatting ($394.3B, 25.3%)
        db.py                  # DuckDB connection + Iceberg table loading
    chat/
        __init__.py
        agent.py               # Claude API + tool use loop
        system_prompt.py       # System prompt generation
        tool_schemas.py        # Tool definitions for Claude API
    cli.py                     # Interactive CLI entry point
    __main__.py                # python -m src.ai_ready
```

### 2.7 Claude API Integration

```python
# Simplified agent loop
import anthropic

client = anthropic.Anthropic()

def chat(user_message: str, history: list[dict]) -> str:
    messages = history + [{"role": "user", "content": user_message}]

    response = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=4096,
        system=build_system_prompt(),
        tools=get_tool_definitions(),
        messages=messages,
    )

    # Tool use loop
    while response.stop_reason == "tool_use":
        tool_results = execute_tool_calls(response)
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
        response = client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=4096,
            system=build_system_prompt(),
            tools=get_tool_definitions(),
            messages=messages,
        )

    return extract_text(response)
```

### 2.8 CLI Interface

```
$ python -m src.ai_ready.cli

SEC EDGAIR Financial Chat
  20 companies | 25 metrics | 7 ratios | FY2009-2026
  Type 'quit' to exit, 'clear' to reset conversation

> What was Apple's revenue in FY2024?

Apple reported revenue of $394.3B in FY2024, up 7.8% year-over-year.
This ranks #1 among all 20 companies (sector: Technology, rank #1 of 5).
Apple's 5-year revenue CAGR is 11.5%.

> How does that compare to Microsoft?

Microsoft reported revenue of $245.1B in FY2024 (note: Microsoft's fiscal
year ends in June, 3 months before Apple's September year-end).

| Metric | Apple | Microsoft |
|--------|-------|-----------|
| Revenue | $394.3B | $245.1B |
| Revenue YoY | +7.8% | +15.7% |
| Net Margin | 25.3% | 35.6% |

⚠️ Fiscal year alignment: Apple FY2024 ends Sep 2024; Microsoft FY2024
ends Jun 2024. These cover different 12-month periods.
```

## 3. CLI Commands

```
python -m src.ai_ready.cli                    # Interactive chat
python -m src.ai_ready.cli --single "question" # Single question, no conversation
python -m src.ai_ready.cli --model claude-sonnet-4-5-20250514  # Model override
```

## 4. DQ Rules

This spec does **not** create new Iceberg tables, so there are no DQ rules in the traditional sense. Instead, tool functions are validated by tests that assert correct results against real Iceberg data.

| Validation | What It Checks |
|-----------|----------------|
| test_real_apple_revenue_fy2024 | get_company_metric("AAPL", "Revenue", 2024) returns known value |
| test_real_boeing_negative_equity | get_company_metric("BA", "Stockholders Equity", 2022) returns negative value with anomaly flag |
| test_real_tech_sector_5_companies | get_sector_summary("Technology", 2024) returns 5 companies |
| test_real_net_margin_rank | rank_companies("Net Margin", 2024) returns all 20 with valid ranks |
| test_fiscal_alignment_warning | compare_companies("AAPL", "MSFT", 2024) includes fiscal year warning |

## 5. Expected Output

Not rows — conversations. The tool functions return structured data; Claude synthesizes it into natural language answers.

**Estimated system prompt:** ~3,000 tokens
**Estimated cost per question:** ~$0.03 (Sonnet, ~8K input + 500 output tokens)
**Prompt caching:** System prompt + tool schemas cached after first turn, reducing cost for multi-turn conversations.

## 6. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Tool use, not text-to-SQL | Claude halluccinates column names and misuses long-format schemas. Validated functions with typed parameters are safer. |
| No embeddings | RAG solves unstructured retrieval. We have structured data + DuckDB. Adding a vector store adds complexity for zero benefit. |
| No pre-computed documents | DuckDB joins in milliseconds. Pre-computing profiles that go stale on data refresh is premature optimization. |
| Anomaly flags at query time | The anomaly rules are static and few (~15). Computing at query time from rules is simpler than maintaining an Iceberg table. |
| System prompt for context, not a registry table | Company roster, metric definitions, and known anomalies fit in ~3K tokens. Governance theater (Iceberg table + DQ rules for static context) adds complexity without value. |
| Sonnet as default model | Good balance of speed, cost, and quality for conversational financial analysis. Opus available via --model flag for complex analysis. |
| Conversation history in memory | Not persisted. Each CLI session starts fresh. Persistence is a future concern. |

## 7. Governance Artifacts

This spec produces fewer governance artifacts than consumable specs because it creates no new stored data:

- `governance/lineage/ai-ready-chat-interface.json` — OpenLineage (reads from all 5 consumable tables, produces no output tables)
- `governance/models/ai-ready-chat-interface-conceptual.md` — Architecture diagram
- No physical/logical models (no new tables)
- No DQ rules (no stored data to validate)
- No DQ scorecard (validation is via tests against real data)

## 8. Testing

```
tests/ai_ready/
    __init__.py
    tools/
        __init__.py
        test_financial_tools.py   # Tool function tests (unit + integration)
        test_anomaly_checker.py   # Anomaly flag tests
        test_formatters.py        # Number formatting tests
        test_db.py                # DB connection tests
    chat/
        __init__.py
        test_system_prompt.py     # System prompt generation tests
        test_tool_schemas.py      # Tool schema validation tests
```

### Key Test Categories

**Unit tests (no Iceberg):**
- Formatter: 394328000000 → "$394.3B", 0.253 → "25.3%", -1200000000 → "($1.2B)"
- Anomaly checker: negative equity → flag, D/E > 50 → flag, normal values → no flag
- Tool parameter validation: invalid ticker → error, missing required params → error

**Integration tests (against real Iceberg):**
- get_company_metric("AAPL", "Revenue", 2024) returns real value with correct formatting
- get_company_profile("BA", 2022) includes negative equity anomaly flag
- compare_companies("AAPL", "MSFT", 2024) includes fiscal alignment warning
- rank_companies("Net Margin", 2024) returns 20 companies with ranks 1-20
- get_sector_summary("Technology", 2024) returns 5 companies
- get_company_trend("AAPL", "Revenue", 2018, 2024) returns 7 data points with CAGR

## 9. Agent Workflow

This spec follows a simplified pipeline — no data modeling gates since no new tables are created:

1. @governance-reviewer — Pre-implementation review
2. @primary-agent — Implementation (tools, chat agent, CLI, system prompt)
3. @primary-agent — Integration testing against real Iceberg data
4. @lineage-tracker — OpenLineage capture (reads-only lineage)
5. @governance-reviewer — Post-implementation check
6. @staff-engineer — Final quality review (including live chat testing)

## 10. Dependencies

- `consumable-company-financials` (🟢 COMPLETE) — 26,894 rows
- `consumable-financial-ratios` (🟢 COMPLETE) — 6,544 rows
- `consumable-period-over-period` (🟢 COMPLETE) — 65,445 rows
- `consumable-peer-comparison` (🟢 COMPLETE) — 26,559 rows
- `consumable-amendment-analysis` (🟢 COMPLETE) — 371 rows
- `anthropic` Python SDK — for Claude API tool use
- `ANTHROPIC_API_KEY` environment variable

## 11. Post-Implementation Governance Review

**Agent:** @governance-reviewer
**Date:** 2026-03-15
**Review Type:** Post-implementation

### Checklist

| Check | Status | Evidence |
|-------|--------|----------|
| Lineage exists | PASS | `governance/lineage/ai-ready-chat-interface.json` — reads from all 5 consumable tables |
| Conceptual model exists | PASS | `governance/models/ai-ready-chat-interface-conceptual.md` |
| Tests pass | PASS | 116 new tests (442 total), all passing |
| Tool functions validated against real data | PASS | Integration tests verify real Iceberg data returns |
| Anomaly flags working | PASS | Boeing negative equity, extreme D/E flagged correctly |
| Fiscal alignment warnings working | PASS | AAPL vs MSFT comparison includes warning |
| Number formatting correct | PASS | 34 formatter tests covering all ranges |
| No new Iceberg tables | PASS | This is an application layer, not a data transformation |

### Verdict: APPROVED

### Notes
This spec intentionally produces no new stored data — it is an application layer that queries the consumable zone via validated tool functions. Governance is lighter than consumable specs: no DQ rules, no physical/logical models, no data dictionary additions. The 116 tests serve as the validation layer.

## 12. Staff Engineer Review

**Agent:** @staff-engineer
**Date:** 2026-03-15
**Spec:** ai-ready-chat-interface
**Production stats:** 442 tests pass, 7 tool functions, 7 anomaly rules, ~3K token system prompt

### Code Review

#### Architecture
The tool-use-over-DuckDB architecture is the right call. The data is structured, small (125K rows), and well-indexed by the consumable zone. Adding RAG/embeddings would be solving a problem that doesn't exist. The 7 tool functions cover the question space well — single metric, full profile, comparison, ranking, trend, sector, ratio.

#### tools/db.py
Loads all 5 consumable tables into in-memory DuckDB via PyIceberg scan -> Arrow -> register. Data is cached after first load. Clean, correct.

#### tools/financial_tools.py
Each tool function follows the same pattern: validate inputs, query DuckDB, format results, check anomalies, return structured dict. Metric resolution supports both names ("Revenue") and IDs ("BT-022") with exact-match priority over partial match. Good edge case handling — unknown tickers return helpful error messages, missing metrics explain why.

#### tools/anomaly_checker.py
7 rules covering the real anomalies found during EDA (Boeing negative equity, Apple Q1 2017 negative revenue, extreme D/E, etc.). Rules are simple predicates, not a rules engine. Correct for the scope.

#### tools/formatters.py
Comprehensive number formatting with 34 test cases. Handles trillions, billions, millions, thousands, per-share, percentages, negatives. No edge case gaps found.

#### chat/agent.py
Standard Claude API tool use loop. Handles multi-turn tool calls correctly. Conversation history managed in memory. ANTHROPIC_API_KEY check on startup with clear error message.

#### chat/system_prompt.py
Dynamic system prompt built from real data — company roster queried from company_financials, not hardcoded. Includes metric definitions, anomaly rules, fiscal alignment info. ~3K tokens.

#### Tests
116 tests covering formatters (34), anomaly checker (19), tool schemas (7), DB connection (7), financial tools (37), system prompt (6). Integration tests query real Iceberg data. No test theater.

### Verdict: APPROVED

Clean architecture, well-tested, correct tool implementations. The hardest part of this codebase — fiscal year alignment and anomaly detection — is handled correctly. 442 tests green. Ship it.
