# CLAUDE.md

Project constitution for Claude Code. Read this before editing anything.

## What this is
An insurance (P&C) semantic layer built on dbt + MetricFlow, running locally on
DuckDB. Synthetic policy/claim/exposure data is enriched with a third-party
vendor feed (a FEMA-style flood file standing in for a commercial vendor like
Verisk or Moody's RMS). The point of the repo is a *trusted* semantic layer:
every metric reconciles to source and is gated in CI before it can reach a
dashboard.

## Stack and commands
- Transform: dbt Core (`dbt build`), warehouse: DuckDB locally (`dev.duckdb`).
- Semantic layer: MetricFlow (`mf`), metrics defined in `models/semantic/`.
- Tests: dbt generic tests + dbt_expectations + singular reconciliation tests.
- Always run with `DBT_PROFILES_DIR` set to the repo root (profiles.yml lives here).

Common commands:
- `python scripts/generate_data.py` regenerate seeds (deterministic, seed=42)
- `dbt seed && dbt build` full build + every test
- `mf validate-configs` validate the semantic layer
- `mf query --metrics loss_ratio --group-by policy__line_of_business`
- `bash scripts/validate.sh` the full gate (build + tests + semantic validation)
- `python scripts/simulate_refresh.py && dbt build` simulate the next ingestion
  batch; the incremental facts process only the new rows

Refresh / incrementality:
- `fct_premium` and `fct_claim` are incremental, keyed on their PK with a
  `loaded_at` watermark. After ANY change to their schema, rebuild with
  `dbt build --full-refresh` (an in-place incremental run against an old table
  shape will fail). CI always builds clean, so it is unaffected.

## Conventions (do not break these)
1. MetricFlow has ONE GLOBAL NAMESPACE. Every entity, dimension, measure, and
   metric name must be unique across the whole project. Prefix measures with
   their domain (e.g. `written_premium_amount`, not `amount`).
2. The time spine is `dim_date`, configured in `models/semantic/_time_spine.yml`.
   Any time-based metric depends on it. Do not remove it.
3. Cross-model metrics (e.g. `loss_ratio` = incurred_loss / earned_premium) join
   through the shared `policy` entity. Group those metrics by entity-qualified
   dimensions: `policy__line_of_business`, `policy__state`.
4. Build new models in parallel; never refactor a model in place without
   re-running the reconciliation tests.

## The trust rule (most important)
A metric is not trusted because Claude wrote it. It is trusted because it
reconciles to source and passes the gate. When you add or change a metric you
MUST also add or update its reconciliation test in `tests/`, and the build must
stay green. Never weaken a reconciliation tolerance to make a test pass.
