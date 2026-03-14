# SEC EDGAIR

AI agent pipeline that takes raw SEC EDGAR XBRL data and delivers it as a clean, tested, governed, semantically meaningful, AI-ready data product.

**Stack:** Python, DuckDB + Apache Iceberg, Claude Code with specialized agents

**Status:** Phase 0 — Setup

## Quick Start

```bash
# Clone and install
git clone <repo-url>
cd sec-edgair
uv sync  # or: poetry install

# Verify DuckDB + Iceberg works
python -c "import duckdb; print(duckdb.__version__)"
```

## Architecture

Raw → Base → Consumable → AI-Ready

Each zone is governed by AI agents that produce lineage, data quality rules, CDE mappings, and audit trails as a byproduct of the transformation work.

## Project Structure

- `src/` — Source code organized by zone
- `data/` — Data files organized by zone (gitignored)
- `governance/` — Governance artifacts (lineage, CDE catalog, data dictionary, audit trail)
- `docs/specs/` — Spec-driven development specs
- `tests/` — Data quality rules and validation tests
- `.claude/agents/` — Agent definitions for Claude Code
