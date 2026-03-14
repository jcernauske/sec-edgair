# Spec: DQ Execution Framework

## Problem Statement

DQ rules are defined in `governance/dq-rules/*.json` (22 rules across 4 specs) with SQL queries and thresholds — but no code ever executes them against real data. Scorecards report test results, not production validation. This deprives the human of the data they need to make governance decisions.

The gap spans the full lifecycle: rules aren't reviewed/approved, aren't executed against Iceberg tables, results aren't stored, and failures don't gate the pipeline.

## Success Criteria

1. All 22 existing DQ rules have lifecycle status fields (status, proposed_by, proposed_at, etc.)
2. `python -m src.infra.dq_runner run` executes SQL rules against real Iceberg tables
3. Results are stored as timestamped JSON in `governance/dq-results/`
4. Scorecards are generated from real execution results, not test results
5. P0 failures block spec completion; P1 warn; P2/P3 informational
6. CLI provides status/approve/run/results/scorecard/acknowledge commands
7. Tests validate threshold evaluation, rule loading, and execution logic

## Zone

Infrastructure (cross-cutting — serves all zones)

## Input

- `governance/dq-rules/*.json` — rule definitions with SQL and thresholds
- Iceberg tables in `data/` — real data to validate

## Output

| Artifact | Path |
|----------|------|
| Execution engine | `src/infra/dq_runner.py` |
| Scorecard generator | `src/infra/dq_scorecard.py` |
| Execution results | `governance/dq-results/{spec}-{timestamp}.json` |
| Updated scorecards | `governance/dq-scorecards/{spec}-scorecard.md` |

## Rule Lifecycle

```
PROPOSED → APPROVED → ACTIVE
```

- **PROPOSED**: @dq-engineer creates rules during spec pipeline
- **APPROVED**: Human approves (when `REQUIRE_HUMAN_APPROVAL=True`); auto-advances when False
- **ACTIVE**: Set automatically on first successful execution against real data

Existing 22 rules get `"status": "active"` retroactively (already implicitly reviewed).

## Execution Engine

Cross-cutting `src/infra/dq_runner.py` — follows the pattern of `src/infra/iceberg_setup.py`.

SQL rules reference `namespace.table` (e.g., `base.financial_facts`). The runner:
1. Parses table references from SQL
2. Loads each via `catalog.load_table()` → PyIceberg scan → Arrow
3. Registers as DuckDB views using `namespace_table` naming
4. Rewrites SQL to use view names
5. Executes and evaluates threshold

## Gating

| Priority | Behavior |
|----------|----------|
| P0 failure | HARD BLOCK — spec cannot be marked complete |
| P1 failure | WARNING — displayed prominently, human decides |
| P2/P3 failure | INFORMATIONAL — logged, no action required |

## CLI Commands

All via `python -m src.infra.dq_runner <command>`:

| Command | Purpose |
|---------|---------|
| `status [--spec NAME]` | Show rule statuses |
| `approve RULE_ID [...]` | Approve proposed rules |
| `run [--spec NAME] [--priority P0]` | Execute rules against real data |
| `results [--spec NAME]` | Show latest run results |
| `scorecard [--spec NAME]` | Generate markdown scorecard |
| `acknowledge --spec NAME --run RUN_ID --reason "..."` | Acknowledge failures |

## Testing

- `tests/infra/test_dq_runner.py` — threshold evaluation, rule loading, SQL execution
- `tests/infra/test_dq_scorecard.py` — scorecard generation from results

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Cross-cutting `src/infra/` not per-module | DQ runner serves all specs/zones |
| Reuse `REQUIRE_HUMAN_APPROVAL` | One toggle, not two |
| Results in `governance/dq-results/` not Iceberg | Governance artifacts belong in git |
| `acknowledge` not `approve` for failures | Semantic precision |
| No scheduler/cron | Local dev pipeline — human runs manually |
| Retroactive `active` status on existing rules | All 22 rules were implicitly reviewed |
