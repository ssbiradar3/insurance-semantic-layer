# Running This in a Company (Production Architecture)

This repo runs locally on DuckDB with synthetic CSV seeds so it works anywhere
with zero infrastructure. This document shows what the **same project** looks like
deployed inside a company against their real databases, dbt, and surrounding
tooling — and exactly what changes (surprisingly little).

## The headline: your logic doesn't change

dbt models, tests, and MetricFlow metrics are warehouse-agnostic. Going to
production is mostly swapping the engine and the infrastructure *around* the
project — not rewriting the project.

| Concern | This repo (demo) | Company / production |
|---|---|---|
| **Warehouse** | DuckDB file (`dev.duckdb`) | Snowflake / BigQuery / Databricks / Redshift |
| **Raw data** | CSV `seeds/` you generate | Real tables landed in the warehouse; declared as dbt `sources` |
| **Ingestion (EL)** | `scripts/generate_data.py` | Fivetran / Airbyte / dlt / CDC from policy-admin & claims systems |
| **Transform** | dbt Core CLI on a laptop | dbt Core in CI/orchestrator, or dbt Cloud — same `dbt build` |
| **Semantic layer** | MetricFlow CLI (`mf query`) | dbt Semantic Layer (hosted MetricFlow), or Cube / LookML / AtScale |
| **Orchestration** | Run commands by hand | Airflow / Dagster / dbt Cloud scheduler on a cron |
| **Auth** | `profiles.yml` → duckdb, no creds | `profiles.yml` → warehouse via env-var / key-pair / SSO secrets |
| **Environments** | One local DB | Separate `dev` / `ci` / `prod` schemas or databases |
| **CI** | GitHub Actions builds DuckDB | CI builds into a throwaway warehouse schema (Slim CI) |
| **Consumption** | `mf query` in the terminal | Tableau / Power BI / Looker, or an API, over the semantic layer |
| **Observability** | The `assert_*` tests | Same tests **+** Elementary / Monte Carlo, freshness, lineage |
| **Governance** | n/a | RBAC, column/row masking for PII, a data catalog (DataHub/Collibra) |

## The one structural code change: `seeds` → `sources`

In the company, raw data already lives in the warehouse, so you declare it as
**sources** (see [`models/staging/_sources.yml`](../models/staging/_sources.yml))
instead of loading seeds. Then each staging model changes **one line**:

```sql
-- models/staging/stg_policies.sql
with source as (
    select * from {{ source('policy_admin', 'policies') }}   -- was ref('raw_policies')
)
select ...
```

Everything downstream — `dim_*`, `fct_*`, semantic models, every metric, and all
the `assert_*` reconciliation tests — is **unchanged**. In fact the reconciliation
tests become *more* valuable: they now tie the gold metric back to the actual
claims/policy system of record, which is exactly what an actuary or auditor wants.

You also get **source freshness** for free:

```bash
dbt source freshness   # alerts if ingestion is stale, before bad data flows downstream
```

## Environments & `profiles.yml`

The repo's [`profiles.yml`](../profiles.yml) ships three targets:

- **`dev`** (default) — local DuckDB, so the demo runs anywhere.
- **`prod`** — Snowflake, all credentials from environment variables / secrets
  (key-pair auth preferred over passwords). Activated with `dbt build --target prod`.
- **`ci`** — Snowflake into an **isolated, throwaway schema per pull request**, so
  CI tests never touch dev or prod data.

```bash
# Production secrets come from the environment / a secrets manager — never committed:
export SNOWFLAKE_ACCOUNT=...   SNOWFLAKE_USER=...
export SNOWFLAKE_PRIVATE_KEY_PATH=/secrets/dbt_key.p8
export SNOWFLAKE_ROLE=TRANSFORMER SNOWFLAKE_DATABASE=ANALYTICS
export SNOWFLAKE_WAREHOUSE=TRANSFORMING SNOWFLAKE_SCHEMA=insurance
dbt build --target prod
```

## Developer workflow, day to day

1. **Connect** — your `dev` target points at the company warehouse with *your own*
   dev schema (e.g. `dbt_sbiradar`), credentials from SSO/env vars. You never
   touch prod directly.
2. **Branch** — `git checkout -b add-combined-ratio`.
3. **Build in isolation** — `dbt build --select +combined_ratio` writes only to
   your dev schema.
4. **Open a PR** — CI builds the changed models into a throwaway schema and runs
   every test, including reconciliation. **Nothing merges red** — the same gate as
   the demo, just on a real warehouse.
5. **Merge → deploy** — the orchestrator runs `dbt build --target prod` on
   schedule, materializing into the prod `marts` / `semantic` schemas.
6. **Consume** — analysts and actuaries hit `loss_ratio`, `combined_ratio` from
   Tableau / Looker via the semantic layer — one governed definition.

## CI/CD (Slim CI)

The demo's gate (`scripts/validate.sh`: `dbt build` + tests + `mf validate-configs`)
becomes a CI job that, at scale, runs only what changed:

```bash
# Build & test ONLY modified models and their downstream dependents:
dbt build --select state:modified+ --defer --state ./prod-manifest --target ci
mf validate-configs
```

`--defer` against the production manifest lets unchanged upstream models read from
prod, so a one-line metric change doesn't rebuild the whole warehouse in CI.

## Orchestration

A scheduler (Airflow / Dagster / dbt Cloud) runs the pipeline on a cadence:

```
ingest (Fivetran/CDC)  ->  dbt source freshness  ->  dbt build --target prod
                                                  ->  mf validate-configs
                                                  ->  publish freshness/metrics to catalog
```

Failures page the on-call data engineer; the reconciliation tests are the
tripwire that stops a silently-wrong number from reaching a dashboard.

## Security & governance (insurance-specific)

- **PII** — policyholder and claims data is sensitive. You develop behind RBAC,
  with row/column masking; dev may only expose de-identified data.
- **Secrets** — warehouse credentials live in a secrets manager / CI secrets,
  never in git. `profiles.yml` only references env vars.
- **Vendor contracts** — `raw_vendor_flood` becomes a real Verisk / Moody's RMS /
  CoreLogic feed with an SLA, monitored by `dbt source freshness`.
- **Lineage & catalog** — `dbt docs` (or DataHub/Collibra) gives column-level
  lineage so anyone can trace `combined_ratio` back to the source tables.

## Observability

Layer data-observability on top of the existing tests:

- **Elementary** (dbt-native) or **Monte Carlo** for anomaly detection, volume,
  and freshness alerts.
- Test results and freshness published to the catalog and a status dashboard.
- Reconciliation tolerances tracked over time — a slowly drifting diff is an early
  warning even before it breaches the gate.

## What stays exactly the same

- The `staging → marts → semantic` structure and all `.sql` / `.yml` model files.
- Every metric definition (simple, ratio, derived).
- The reconciliation-to-source philosophy and the `assert_*` tests.
- The trust rule and the CI gate.

That portability is the whole point — and the reason this is a credible portfolio
piece: it demonstrates the part of the job that *doesn't* change between a laptop
and a Fortune-500 warehouse.
