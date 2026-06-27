# Observability & Monitoring

How this project answers "is the data healthy, and would we know if it broke?" —
and an honest note on tool choice for a zero-infra DuckDB demo.

## What is monitored today (runs in the gate)

| Concern | Implementation |
|---|---|
| **Volume anomalies** | `dbt_expectations.expect_table_row_count_to_be_between` on `fct_premium` and `fct_claim` — alerts if the table size falls outside an expected band (rows silently dropped or fanned out). |
| **Correctness / drift** | The five `assert_*` reconciliation tests — gold metrics must tie to the source of record on every build. |
| **Schema & integrity** | `unique`, `not_null`, `relationships`, `accepted_values`, range checks at every layer. |
| **Logic regressions** | A dbt **unit test** pins the earned-premium proration math. |
| **History / change** | The SCD2 `policy_status_snapshot` records status transitions. |
| **Freshness** | Declared on the production `sources` (`models/staging/_sources.yml`); `dbt source freshness` alerts when ingestion is stale. (No-op in the seed-based demo, since seeds have no live ingestion clock.) |

## The report

`dbt docs` generates an interactive observability site — the full lineage DAG
(sources → staging → marts → snapshot → metrics), every model/column description,
and the latest test results:

```bash
bash scripts/docs.sh        # dbt docs generate + serve at http://localhost:8080
```

This is DuckDB-compatible and needs zero extra infrastructure.

## Why not Elementary here (and how to enable it in production)

[Elementary](https://www.elementary-data.com/) is the production-standard dbt-native
observability package — anomaly detection (volume, freshness, column-level),
test-result history, and a hosted HTML report. I evaluated it for this repo and
**it does not support DuckDB**: its artifact models fail to compile on DuckDB
(`syntax error at or near "meta"`, `cannot start a transaction within a
transaction`). Its supported adapters are Snowflake, BigQuery, Redshift,
Databricks, and Postgres.

Rather than break the zero-infra demo, I implemented the **same capability
natively** (volume monitors above + the `dbt docs` lineage/catalog report). On a
real warehouse you drop Elementary in with a one-line change — it's already
stubbed in [`packages.yml`](../packages.yml):

```yaml
# packages.yml (uncomment on Snowflake/BigQuery/etc.)
- package: elementary-data/elementary
  version: [">=0.16.0", "<0.20.0"]
```

```yaml
# dbt_project.yml
models:
  elementary:
    +schema: elementary
```

```bash
dbt deps && dbt run --select elementary    # creates the result-storage models
pip install elementary-data && edr report  # generates the observability report
```

Then Elementary's anomaly tests (`elementary.volume_anomalies`,
`elementary.freshness_anomalies`, `elementary.column_anomalies`) replace the
native row-count guards, accumulating history across runs for true anomaly
detection.

## The takeaway

The monitoring *capability* — volume, correctness, freshness, history, lineage —
is present and runs in CI today. Elementary is the production upgrade for richer
anomaly detection once the project is on a supported warehouse. Choosing a
working native equivalent over a tool that can't run on the target engine is the
engineering call, and the migration path is one line.
