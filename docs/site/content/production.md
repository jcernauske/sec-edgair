---
title: Production Deployment
description: "Four deployment paths for taking SEC EDGAIR from 20 companies on a laptop to 10,000 companies with SLAs. AWS, Azure, Snowflake, and Databricks -- what changes, what stays, and what it costs."
---

# Production Deployment

**You have seen the architecture work at 20 companies. Here is what changes at 10,000.**

This is not a rewrite proposal. The current architecture -- Python + DuckDB + PyIceberg + SQLite catalog -- is correctly designed. The zone boundaries are clean, the DQ gates are structural, the lineage is runtime, and the governance metadata travels with the data. The question is not "does this design work?" but "what infrastructure replaces the laptop parts when you need SLAs, concurrent users, and 500x more data?"

## What Already Scales (Do Not Touch)

Before talking about what changes, here is what stays the same on every platform. These are architectural decisions, not implementation details, and they are correct:

- **Four-zone medallion structure.** Raw, Base, Consumable, AI-Ready. Each zone reads only from the prior zone. This is the pattern every lakehouse vendor recommends because it works.
- **Iceberg as the table format.** Every platform on this list supports Iceberg natively or is racing to. The Parquet data files written by this pipeline are already in the right format.
- **DQ rules as JSON governance artifacts.** The 128 rules in `governance/dq-rules/` are SQL-based, priority-tagged, and lifecycle-managed. They execute against any SQL engine, not just DuckDB.
- **OpenLineage-compatible event schema.** The `governance.lineage_events` table uses a schema that maps directly to OpenLineage START/COMPLETE/FAIL semantics. Any lineage platform (Marquez, DataHub, Atlan) can ingest these events.
- **Promote-then-validate pattern.** Every promote function calls `validate_after_write()`. This is the lakehouse equivalent of database constraints and it works regardless of compute engine.
- **Governance artifacts as code.** Business glossary, CDE catalog, concept priority rules, entity resolution mappings -- all versioned JSON in `governance/`. This is GitOps for data governance, and it ports to any platform without modification.

## What Must Change (And Why)

Three components are deliberately single-user/single-machine and need replacement at scale:

| Component | Current | Why It Must Change |
|-----------|---------|-------------------|
| **Catalog** | SQLite-backed PyIceberg `SqlCatalog` | No concurrent writers. One person runs the pipeline at a time. |
| **Storage** | Local filesystem (`data/` directory) | Cannot be shared across compute nodes. No durability guarantees. |
| **Orchestration** | CLI commands (`python -m src.base.conformed_facts.cli build`) | No scheduling, no retry, no dependency graph, no alerting. |
| **Compute** | In-process DuckDB | Single-node. Works beautifully to ~10M rows, then you need distributed compute for the heavy joins. |
| **Monitoring** | DQ scorecards as markdown files | No alerting, no dashboards, no SLA tracking. |

Everything else -- the Python transformation logic, the DQ rule definitions, the lineage event emission, the governance metadata structure -- ports directly.

---

## AWS: S3 + Glue Catalog + Step Functions

### Architecture

```
SEC EDGAR API
    |
    v
Lambda (raw ingest, 15-min timeout is fine for bulk ZIP download)
    |
    v
S3 bucket: s3://sec-edgair-{env}/raw/
    |
    v
Step Functions state machine (orchestrates zone transitions)
    |
    v
Glue ETL Jobs (Spark, Python shell) or Athena queries
    - base zone: entity resolution, tag normalization, conformed facts
    - consumable zone: ratios, growth, peer comparison
    |
    v
S3 bucket: s3://sec-edgair-{env}/{zone}/iceberg_warehouse/
    |
    v
Athena (ad-hoc queries) + Lambda (AI-Ready tool functions)
```

### What Changes

| Component | Local | AWS |
|-----------|-------|-----|
| Catalog | SQLite file | AWS Glue Data Catalog (native Iceberg support since 2023) |
| Storage | `data/` directory | S3 with Iceberg table format |
| Compute | DuckDB in-process | Glue ETL (PySpark for heavy joins) or Athena (SQL-only transforms) |
| Orchestration | CLI | Step Functions with EventBridge schedules |
| DQ execution | `python -m src.infra.dq_runner run` | Glue Python Shell job, same SQL engine (Athena), results to S3 |
| Lineage | Iceberg table in `data/governance/` | Same events emitted to S3-backed Iceberg table; Glue lineage view in Data Catalog |
| AI-Ready | Local Python + Claude API | Lambda functions behind API Gateway, same tool function signatures |

### Iceberg Strategy

- **Catalog:** Glue Data Catalog. It is the only AWS-native option with cross-service compatibility (Athena, EMR, Redshift Spectrum all read from it). Do not use a standalone Hive Metastore unless you enjoy suffering.
- **Storage:** Single S3 bucket, prefixed by zone: `raw/`, `base/`, `consumable/`, `governance/`. Iceberg manages the file layout.
- **Partitioning:** `base.financial_facts` partitioned by `company_cik` (20 companies = 20 partitions now, scales to 10K). `consumable.company_financials` partitioned by `fiscal_year` for time-based queries. `raw.xbrl_company_facts` partitioned by `cik` to parallelize ingest.
- **Compaction:** Glue ETL job on a daily schedule to compact small Parquet files. Iceberg's `rewrite_data_files` procedure. At 10K companies, expect ~50K files without compaction.

### DQ at Scale

The current DQ runner executes SQL against DuckDB via `iceberg_scan()`. On AWS, the same SQL runs against Athena. The change is mechanical:

1. Replace `duckdb.connect()` + `iceberg_scan()` with `boto3.client('athena').start_query_execution()`.
2. Results still write to `governance/dq-results/` (now an S3 prefix).
3. P0 failures still block the Step Functions state machine -- the Glue job exits non-zero, Step Functions catches the failure and halts the pipeline.
4. Add SNS topic for DQ failure alerting. CloudWatch alarm on the Step Functions failure state.

### Cost Model (10K Companies)

| Service | Monthly Estimate | Notes |
|---------|-----------------|-------|
| S3 storage | $50-100 | ~500GB Iceberg data (Parquet + metadata). S3 Standard. |
| Glue ETL | $200-400 | 10 DPU-hours/day for base zone transforms. Spot instances. |
| Athena | $50-100 | DQ rules + ad-hoc queries. ~500GB scanned/month at $5/TB. |
| Step Functions | $5 | State transitions are cheap. |
| Lambda | $20 | Raw ingest + AI-Ready tool functions. |
| Glue Catalog | $1 | First million objects free. |
| **Total** | **$325-625/month** | |

### Timeline

- **Week 1:** S3 bucket + Glue Catalog setup. Port `iceberg_setup.py` to use Glue Catalog instead of SQLite. Raw ingest Lambda. Validate one table end-to-end.
- **Month 1:** All zone transforms running as Glue jobs. Step Functions state machine. DQ runner ported to Athena. Lineage events writing to S3.
- **Quarter 1:** Incremental refresh (change detection on SEC EDGAR filing dates). CloudWatch dashboards. Multi-environment (dev/staging/prod). CI/CD pipeline.

---

## Azure: ADLS Gen2 + Unity Catalog + Data Factory

### Architecture

```
SEC EDGAR API
    |
    v
Azure Function (raw ingest)
    |
    v
ADLS Gen2: abfss://sec-edgair@{account}.dfs.core.windows.net/raw/
    |
    v
Data Factory pipeline (orchestration)
    |
    v
Azure Databricks (Spark) or Synapse Serverless SQL
    - base zone transforms
    - consumable zone transforms
    |
    v
ADLS Gen2: abfss://sec-edgair@{account}.dfs.core.windows.net/{zone}/
    |
    v
Synapse Serverless SQL (ad-hoc) + Azure Function (AI-Ready)
```

### What Changes

| Component | Local | Azure |
|-----------|-------|-------|
| Catalog | SQLite file | Unity Catalog (if Databricks) or Synapse Lake Database (if pure Azure) |
| Storage | `data/` directory | ADLS Gen2 with hierarchical namespace |
| Compute | DuckDB in-process | Databricks clusters or Synapse Spark pools |
| Orchestration | CLI | Azure Data Factory with trigger schedules |
| DQ execution | `dq_runner.py` | Synapse Serverless SQL pool running the same DQ SQL |
| AI-Ready | Local Python + Claude API | Azure Function + Claude API (or swap to Azure OpenAI) |

### Iceberg Strategy

Azure's Iceberg story has two paths:

1. **Databricks on Azure (recommended):** Unity Catalog manages Iceberg tables natively. Delta Lake is Databricks' preferred format, but Unity Catalog supports Iceberg via UniForm -- writes Delta, reads as Iceberg. This gives you the best of both: Delta's optimization features (Z-order, liquid clustering) with Iceberg compatibility for external tools.
2. **Pure Azure (Synapse):** Synapse Serverless SQL can read Iceberg tables from ADLS Gen2. Less mature than the Databricks path. You manage the Iceberg catalog yourself (Hive Metastore on Azure SQL or the Nessie catalog).

Go with option 1 unless you have a contractual reason to avoid Databricks.

### DQ at Scale

- DQ SQL rules execute as Synapse Serverless SQL queries or Databricks SQL queries. Same SQL, different engine.
- Data Factory pipeline has a "DQ gate" activity after each transform activity. Gate checks the DQ result JSON in ADLS Gen2. Failure halts the pipeline.
- Azure Monitor alert rules on Data Factory pipeline failures. Integration with PagerDuty/Slack via Logic Apps.

### Cost Model (10K Companies)

| Service | Monthly Estimate | Notes |
|---------|-----------------|-------|
| ADLS Gen2 | $30-60 | ~500GB, hot tier. Cheaper than S3 for large files. |
| Databricks | $400-800 | Standard tier, 2-4 node cluster, auto-scaling. Heaviest cost. |
| Data Factory | $50-100 | Pipeline orchestration + data movement activities. |
| Synapse Serverless | $50-100 | DQ queries + ad-hoc analysis. Pay-per-query. |
| Azure Functions | $15 | Raw ingest + AI-Ready endpoints. |
| **Total** | **$545-1,075/month** | |

Azure is more expensive than AWS primarily because Databricks licensing adds to the compute cost. If you go pure Synapse (no Databricks), drop the estimate to $300-600/month, but you lose Unity Catalog's lineage features and the Iceberg story gets weaker.

### Timeline

- **Week 1:** ADLS Gen2 storage account + Databricks workspace. Port catalog setup to Unity Catalog. One table end-to-end.
- **Month 1:** All transforms as Databricks notebooks or jobs. Data Factory pipeline. DQ runner ported.
- **Quarter 1:** Unity Catalog lineage integration (auto-captures column-level lineage). Incremental refresh. Purview integration for enterprise governance.

---

## Snowflake: Managed Iceberg Tables + Snowpark

### Architecture

```
SEC EDGAR API
    |
    v
Snowpark Python UDF or external stage load (raw ingest)
    |
    v
Snowflake-managed Iceberg table: raw.xbrl_company_facts
    |
    v
Snowflake Tasks + DAG (orchestration)
    |
    v
Snowpark Python (transforms) or Snowflake SQL
    - base zone: entity resolution, tag normalization, conformed facts
    - consumable zone: ratios, growth, peer comparison
    |
    v
Snowflake-managed Iceberg tables: base.*, consumable.*
    |
    v
Snowflake Cortex or external Claude API (AI-Ready)
```

### What Changes

| Component | Local | Snowflake |
|-----------|-------|-----------|
| Catalog | SQLite file | Snowflake's internal catalog (Polaris Catalog for external access) |
| Storage | `data/` directory | Snowflake-managed storage (or external S3/GCS/ADLS with Iceberg) |
| Compute | DuckDB in-process | Snowflake virtual warehouses (auto-suspend, auto-scale) |
| Orchestration | CLI | Snowflake Tasks with CRON schedules and DAG dependencies |
| DQ execution | `dq_runner.py` | Snowflake SQL executing the same DQ rule SQL directly |
| Lineage | Iceberg table | ACCESS_HISTORY + OBJECT_DEPENDENCIES views (built-in) |
| AI-Ready | Local Python + Claude API | Snowpark Container Services or external API |

### Why Snowflake Is Interesting Here

Snowflake is the path of least resistance for this specific project, for one reason: **the DQ rules are already SQL.** All 128 rules in `governance/dq-rules/` are SQL queries with threshold expressions. They run on Snowflake without modification (after replacing `namespace.table` references, which the current `_rewrite_sql()` function already handles).

The Python transformation logic in `src/base/` and `src/consumable/` uses DuckDB SQL via PyIceberg scan. Snowpark Python provides the same pattern: read Iceberg table into a DataFrame, transform, write back. The `promote.py` files need the least modification on Snowflake.

### Iceberg Strategy

- **Snowflake-managed Iceberg tables** (GA since 2024). Snowflake manages the catalog, storage, and compaction. You write to them like regular Snowflake tables. External tools (Spark, DuckDB, Trino) can read them via Iceberg REST Catalog (Polaris).
- **Partitioning:** Snowflake handles micro-partitioning automatically. You do not declare partition columns. Snowflake's query optimizer prunes partitions based on query predicates. This is a genuine advantage over the explicit partitioning you need on AWS/Azure.
- **Time travel:** Snowflake's native time travel (up to 90 days on Enterprise) replaces PyIceberg's snapshot-based time travel. The `get_snapshots()` and `read_with_duckdb(snapshot_id=...)` functions map to `SELECT * FROM table AT(TIMESTAMP => ...)`.

### DQ at Scale

This is where Snowflake shines. The DQ runner becomes trivially simple:

1. Load rule JSON files (same `governance/dq-rules/*.json`).
2. Execute each SQL rule as a Snowflake SQL statement. No iceberg_scan, no view registration, no Arrow bridge. Just SQL.
3. Evaluate thresholds (same `evaluate_threshold()` function).
4. Write results to a `governance.dq_results` table (or S3/GCS external stage for portability).
5. Snowflake Tasks check DQ results before proceeding to the next zone. Task DAG dependencies enforce the gate.

Snowflake Alerts (built-in) can notify on P0 failures. No SNS, no CloudWatch, no Logic Apps.

### Cost Model (10K Companies)

| Service | Monthly Estimate | Notes |
|---------|-----------------|-------|
| Snowflake compute | $300-600 | Standard edition, X-Small warehouse (auto-suspend after 60s). Base zone transforms ~2 hours/day. |
| Snowflake storage | $40-80 | ~500GB compressed. $40/TB/month. |
| Snowpark | $0 | Included in compute. |
| Snowflake Tasks | $0 | Included (uses warehouse compute). |
| **Total** | **$340-680/month** | |

The cost advantage of Snowflake is simplicity: one bill, one vendor, one set of credentials. The cost disadvantage is vendor lock-in, mitigated by the Iceberg table format (you can always read the Parquet files from external tools).

### Timeline

- **Week 1:** Snowflake account + database/schema setup matching the current namespace structure (`raw`, `base`, `consumable`, `governance`). Create managed Iceberg tables matching current schemas. Load raw data via `COPY INTO`.
- **Month 1:** All transforms ported to Snowpark Python or pure SQL. Task DAG replacing CLI. DQ runner executing natively. Lineage via ACCESS_HISTORY.
- **Quarter 1:** Incremental refresh via Snowflake Streams (CDC on raw tables). Cortex ML functions for anomaly detection on DQ metrics. Polaris Catalog for external Iceberg access.

---

## Databricks: Unity Catalog + Delta/Iceberg + Workflows

### Architecture

```
SEC EDGAR API
    |
    v
Databricks Job (Python task, raw ingest)
    |
    v
Unity Catalog: sec_edgair.raw.xbrl_company_facts (Delta + UniForm)
    |
    v
Databricks Workflows (orchestration with task dependencies)
    |
    v
Databricks Spark or DuckDB-on-Databricks (yes, this works)
    - base zone transforms
    - consumable zone transforms
    |
    v
Unity Catalog: sec_edgair.{zone}.{table}
    |
    v
Databricks SQL warehouse (ad-hoc) + Model Serving (AI-Ready)
```

### What Changes

| Component | Local | Databricks |
|-----------|-------|------------|
| Catalog | SQLite file | Unity Catalog (three-level namespace maps perfectly to current structure) |
| Storage | `data/` directory | Cloud storage (S3/ADLS/GCS) managed by Unity Catalog |
| Compute | DuckDB in-process | Databricks clusters (or Serverless SQL for DQ) |
| Orchestration | CLI | Databricks Workflows with task dependencies |
| DQ execution | `dq_runner.py` | Databricks SQL or DuckDB extension on Databricks |
| Lineage | Iceberg table | Unity Catalog lineage (automatic column-level lineage) |
| AI-Ready | Local Python + Claude API | Model Serving endpoint or external Claude API |

### Why Databricks Is The Most Natural Fit

The current codebase already uses the exact abstractions that Databricks provides:

1. **Three-level namespace.** The project uses `namespace.table` everywhere (`base.financial_facts`, `consumable.company_financials`). Unity Catalog uses `catalog.schema.table`. Add one level and the naming is identical: `sec_edgair.base.financial_facts`.

2. **PyIceberg compatibility.** Unity Catalog speaks the Iceberg REST Catalog protocol. The `get_catalog()` function in `iceberg_setup.py` can point to Unity Catalog's REST endpoint instead of SQLite. The PyIceberg write path works unchanged.

3. **DuckDB on Databricks.** Databricks supports DuckDB as a library on clusters. The existing DuckDB-based transforms can run without modification while you incrementally migrate to Spark for the joins that need distributed compute.

4. **Automatic lineage.** Unity Catalog captures column-level lineage automatically for any Spark SQL or DataFrame operation. The custom `lineage.py` emission becomes a supplemental signal (DQ results, row counts) rather than the primary lineage source.

### Iceberg Strategy

- **Delta Lake with UniForm.** Databricks writes Delta format and generates Iceberg metadata via UniForm. External tools (DuckDB, Trino, Snowflake) read the tables as Iceberg. You get Delta's optimization features (Z-order, liquid clustering, predictive I/O) with Iceberg's openness.
- **Catalog:** Unity Catalog. Shared across all workspaces. Supports fine-grained access control at the column level (relevant for any PII flags).
- **Partitioning:** Liquid clustering replaces traditional partitioning on Databricks. Specify clustering columns (`company_cik`, `fiscal_year`) and Databricks optimizes the layout incrementally. No partition management overhead.

### DQ at Scale

Databricks has a built-in option and a custom option:

1. **Built-in: Databricks Lakehouse Monitoring.** Automatic statistical profiling, drift detection, and anomaly alerts on Delta tables. Good for the "is the data weird?" question. Does not replace the custom DQ rules (which encode business logic like "no superseded facts in conformed_facts"), but complements them.

2. **Custom: Port the DQ runner.** Run the existing SQL rules against Databricks SQL Serverless warehouse. The `_register_iceberg_views()` function is unnecessary -- Unity Catalog resolves `base.financial_facts` directly. Simplify `run_rules()` to execute SQL via `databricks-sql-connector` Python package.

3. **Workflow gate:** Databricks Workflows supports task dependencies with conditions. The DQ task writes a status flag. The next zone's tasks depend on that flag. P0 failure = pipeline stops.

### DuckDB-on-Databricks Migration Path

This is the pragmatic migration that no one talks about:

1. **Week 1:** Run the existing Python code as Databricks Jobs with DuckDB. Zero code changes. DuckDB reads from Unity Catalog via the Iceberg REST protocol. This works today.
2. **Month 1:** Identify the 2-3 transforms that are slow on single-node DuckDB (likely `conformed_facts` build with the full collision resolution join, and `period_over_period` with the 5-year window). Rewrite those in Spark SQL.
3. **Quarter 1:** Everything that benefits from distribution runs on Spark. Everything that is fast enough on single-node stays on DuckDB. This is the correct hybrid, not "rewrite everything in Spark."

### Cost Model (10K Companies)

| Service | Monthly Estimate | Notes |
|---------|-----------------|-------|
| Databricks compute | $350-700 | Jobs clusters (auto-terminate). Serverless SQL for DQ. |
| Cloud storage | $40-80 | S3/ADLS/GCS, ~500GB. |
| Unity Catalog | $0 | Included with Databricks. |
| Workflows | $0 | Included (uses cluster compute). |
| **Total** | **$390-780/month** | |

### Timeline

- **Week 1:** Databricks workspace + Unity Catalog. Create `sec_edgair` catalog with `raw`, `base`, `consumable`, `governance` schemas. Run existing Python code as a Databricks Job with DuckDB. One table end-to-end.
- **Month 1:** All transforms running as Databricks Jobs. Workflows DAG. DQ runner ported to Databricks SQL. Unity Catalog lineage active.
- **Quarter 1:** Incremental refresh via Delta CDF (Change Data Feed). Lakehouse Monitoring for drift detection. Selective Spark migration for heavy transforms. Asset bundles for CI/CD.

---

## Platform Comparison

| Dimension | AWS | Azure | Snowflake | Databricks |
|-----------|-----|-------|-----------|------------|
| **Iceberg maturity** | Good (Glue Catalog) | Fair (needs Databricks) | Good (managed Iceberg) | Best (UniForm) |
| **Migration effort** | Medium | Medium-High | Medium-Low | Low |
| **DQ rule portability** | High (SQL is SQL) | High | Highest (native SQL) | High |
| **Lineage integration** | Manual (Glue + custom) | Good (Unity/Purview) | Fair (ACCESS_HISTORY) | Best (Unity auto-lineage) |
| **Vendor lock-in risk** | Low (all open formats) | Medium (Purview/Synapse) | Medium (Snowflake SQL) | Low (Delta+Iceberg) |
| **Monthly cost (10K)** | $325-625 | $545-1,075 | $340-680 | $390-780 |
| **Operational complexity** | High (many services) | High (many services) | Low (one service) | Medium |
| **Best for** | AWS-native shops | Microsoft shops | SQL-first teams | Data engineering teams |

## My Recommendation

If I had to pick one platform to deploy this project to production tomorrow, here is my order:

1. **Databricks** -- lowest migration effort because the namespace structure, PyIceberg patterns, and even DuckDB itself port directly. Unity Catalog gives you lineage for free. The DuckDB-on-Databricks bridge means you can run the existing code on day 1 and migrate incrementally.

2. **Snowflake** -- if your team is SQL-first and you want the simplest operational model. One service, one bill, DQ rules run natively. The trade-off is less flexibility for the Python transformation code.

3. **AWS** -- if you are already in AWS and want to minimize vendor lock-in. More operational surface area, but all open-source components. Best long-term optionality.

4. **Azure** -- only if you are a Microsoft shop. The Iceberg story requires Databricks anyway, so you are really choosing Databricks-on-Azure, not "Azure."

## What I Would Not Do

- **Do not rewrite the DQ rules.** They are SQL. They work on every platform. Port the runner, keep the rules.
- **Do not replace the governance metadata structure.** The JSON artifacts in `governance/` are the right abstraction. They are code-reviewable, version-controlled, and platform-independent.
- **Do not start with Spark.** Start with DuckDB on whatever platform you choose. Migrate to Spark only for the transforms that demonstrably need distribution. Most of this pipeline will never need Spark.
- **Do not build a custom catalog.** Use whatever catalog your platform provides. The current SQLite catalog was always meant to be replaced.
- **Do not skip incremental refresh.** Full rebuilds work at 20 companies because they take seconds. At 10K companies, the base zone rebuild will take hours. Change detection on SEC EDGAR filing dates (they have a `filed` date) is the first optimization to build.

---

[Back to home](index.md) | [Architecture](architecture.md) | [Governance](governance.md)
